import base64
import io

from odoo import _, api, fields, models

# match ชื่อ column ใน row แรก (lowercase + strip) -> field
HEADER_MAP = {
    "year": "year",
    "employee code": "employee_code",
    "date att": "date_att",
    "over leave day": "over_leave_day",
}


class ImportTigerSoft(models.Model):
    _name = "ykk.kpi.import.tiger.soft"
    _description = "Import Tiger Soft"
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
        - ยังไม่มี -> insert"""
        self.ensure_one()
        # ถ้ายังไม่มี line แต่มีไฟล์ -> parse จากไฟล์ก่อน (กันกรณี onchange ไม่ทำงาน)
        if not self.line_ids and self.upload_file:
            self.write({"line_ids": self._build_line_commands()})
        Emp = self.env["hr.employee"]
        History = self.env["ykk.kpi.employee.history"]
        now = fields.Datetime.now()
        inserted = updated = 0
        not_found = []
        for line in self.line_ids:
            employee = line.employee_id or Emp.search(
                [("ykk_employee_code", "=", line.employee_code)], limit=1
            )
            if not employee:
                not_found.append(line.employee_code)
                continue
            existing = History.search([
                ("employee_id", "=", employee.id),
                ("year", "=", line.year),
            ], limit=1)
            vals = {
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
        if not_found:
            message += _("\nไม่พบ Employee Code: %s") % ", ".join(not_found)
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
    _description = "Import Tiger Soft Line"

    import_id = fields.Many2one(
        "ykk.kpi.import.tiger.soft", required=True, ondelete="cascade"
    )
    year = fields.Integer(string="Year")
    employee_code = fields.Char(string="Employee Code")
    employee_id = fields.Many2one("hr.employee", string="Employee")
    date_att = fields.Float(string="Date ATT")
    over_leave_day = fields.Float(string="Over Leave Day")
    action_type = fields.Selection(
        [("insert", "Insert"), ("update", "Update")], string="Action"
    )
