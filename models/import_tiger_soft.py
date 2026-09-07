import base64
import io

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

# match ชื่อ column ใน row แรก (lowercase + strip) -> field
HEADER_MAP = {
    "year": "year",
    "salary": "salary",
    "employee code": "employee_code",
    "date att": "date_att",
    "over leave day": "over_leave_day",
}


class ImportTigerSoft(models.Model):
    _name = "ykk.kpi.import.tiger.soft"
    _description = "Import HR Data"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "id desc"

    name = fields.Char(string="Reference", default="New", readonly=True, copy=False)
    user_id = fields.Many2one(
        "res.users", string="Uploaded By",
        default=lambda self: self.env.user, readonly=True,
    )
    upload_file = fields.Binary(string="Upload")
    upload_filename = fields.Char(string="File Name")
    line_ids = fields.One2many(
        "ykk.kpi.import.tiger.soft.line", "import_id", string="Data"
    )
    company_id = fields.Many2one(
        "res.company", default=lambda self: self.env.company
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", "New") == "New":
                vals["name"] = self.env["ir.sequence"].next_by_code("ykk.kpi.import.tiger.soft") or "New"
        return super().create(vals_list)

    def _parse_rows(self):
        """อ่านไฟล์ excel -> list ของ dict ต่อแถว (match จากชื่อ column ใน row แรก)"""
        self.ensure_one()
        import openpyxl  # lazy import: ไม่ให้ module โหลดล้มเหลวหาก env ไม่มี openpyxl
        rows_out = []
        if not self.upload_file:
            return rows_out
        data = base64.b64decode(self.upload_file)
        workbook = openpyxl.load_workbook(io.BytesIO(data), data_only=True)
        sheet = workbook.active
        rows = list(sheet.iter_rows(values_only=True))
        if not rows:
            return rows_out
        headers = [str(h).strip().lower() if h is not None else "" for h in rows[0]]
        col = {}
        for index, header in enumerate(headers):
            if header in HEADER_MAP:
                col[HEADER_MAP[header]] = index

        def cell(row, field):
            idx = col.get(field)
            if idx is None or idx >= len(row):
                return None
            return row[idx]

        for row in rows[1:]:
            if row is None or all(c is None for c in row):
                continue
            year = cell(row, "year")
            emp_code = cell(row, "employee_code")
            rows_out.append({
                "year": int(year) if year not in (None, "") else 0,
                "salary": float(cell(row, "salary") or 0),
                "employee_code": str(emp_code).strip() if emp_code not in (None, "") else "",
                "date_att": float(cell(row, "date_att") or 0),
                "over_leave_day": float(cell(row, "over_leave_day") or 0),
            })
        return rows_out

    def _build_line_commands(self):
        """อ่านไฟล์ -> command สำหรับ line_ids (พร้อมระบุ insert/update)"""
        Emp = self.env["hr.employee"]
        History = self.env["ykk.kpi.employee.history"]
        commands = [(5, 0, 0)]
        for data in self._parse_rows():
            employee = Emp.search(
                [("ykk_employee_code", "=", data["employee_code"])], limit=1
            )
            action_type = "insert"
            if employee:
                existing = History.search([
                    ("employee_id", "=", employee.id),
                    ("year", "=", data["year"]),
                ], limit=1)
                action_type = "update" if existing else "insert"
            commands.append((0, 0, {
                "year": data["year"],
                "salary": data["salary"],
                "employee_code": data["employee_code"],
                "employee_id": employee.id if employee else False,
                "date_att": data["date_att"],
                "over_leave_day": data["over_leave_day"],
                "action_type": action_type,
            }))
        return commands

    @api.onchange("upload_file")
    def _onchange_upload_file(self):
        """หลังเลือกไฟล์ -> อ่านข้อมูลและแสดงในแท็บ"""
        self.line_ids = self._build_line_commands() if self.upload_file else [(5, 0, 0)]

    def action_update_data(self):
        """update ข้อมูลเข้า KPI History ของพนักงาน
        - มี (Year + Employee code) แล้ว -> update
        - ยังไม่มี -> insert
        - ถ้ามี Employee Code ที่ไม่พบ -> ยกเลิกการ import ทั้งหมด"""
        self.ensure_one()
        # ถ้ายังไม่มี line แต่มีไฟล์ -> parse จากไฟล์ก่อน (กันกรณี onchange ไม่ทำงาน)
        if not self.line_ids and self.upload_file:
            self.write({"line_ids": self._build_line_commands()})
        Emp = self.env["hr.employee"]
        History = self.env["ykk.kpi.employee.history"]
        now = fields.Datetime.now()
        inserted = updated = 0
        resolved_lines = []
        not_found = []

        # ตรวจสอบ Employee Code ทุกบรรทัดก่อนเริ่มเขียนข้อมูล เพื่อป้องกัน
        # partial import เมื่อมีข้อมูลแม้เพียงหนึ่งบรรทัดที่ไม่ match
        for line in self.line_ids:
            employee = Emp.search(
                [("ykk_employee_code", "=", line.employee_code)], limit=1
            )
            if not employee:
                not_found.append(line.employee_code or _("(empty)"))
            else:
                resolved_lines.append((line, employee))

        if not_found:
            missing_codes = list(dict.fromkeys(not_found))
            missing_codes_text = ", ".join(missing_codes)
            raise ValidationError(
                _(
                    "Cannot import data because the following Employee Code(s) "
                    "were not found:\n%s"
                )
                % missing_codes_text
            )

        for line, employee in resolved_lines:
            existing = History.search([
                ("employee_id", "=", employee.id),
                ("year", "=", line.year),
            ], limit=1)
            vals = {
                "salary": line.salary,
                "date_att": line.date_att,
                "over_leave_day": line.over_leave_day,
                "update": now,
            }
            if existing:
                existing.write(vals)
                updated += 1
            else:
                vals.update({"employee_id": employee.id, "year": line.year})
                History.create(vals)
                inserted += 1

        message = _("Insert: %s รายการ, Update: %s รายการ") % (inserted, updated)
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Update เสร็จแล้ว"),
                "message": message,
                "type": "success",
                "sticky": False,
            },
        }


class ImportTigerSoftLine(models.Model):
    _name = "ykk.kpi.import.tiger.soft.line"
    _description = "Import HR Data Line"

    import_id = fields.Many2one(
        "ykk.kpi.import.tiger.soft", required=True, ondelete="cascade"
    )
    year = fields.Integer(string="Year")
    employee_code = fields.Char(string="Employee Code")
    employee_id = fields.Many2one("hr.employee", string="Employee")
    date_att = fields.Float(string="Date ATT")
    over_leave_day = fields.Float(string="Over Leave Day")
    salary = fields.Float(string="Salary")
    action_type = fields.Selection(
        [("insert", "Insert"), ("update", "Update")], string="Action"
    )
