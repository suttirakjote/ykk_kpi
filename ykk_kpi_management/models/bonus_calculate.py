import base64
import io

import xlsxwriter

from odoo import api, fields, models


class BonusCalculate(models.Model):
    _name = "ykk.kpi.bonus.calculate"
    _description = "Bonus Calculate"
    _order = "id desc"

    name = fields.Char(string="Reference", default="New", copy=False, readonly=True)
    period_id = fields.Many2one("ykk.kpi.period", string="Period")
    responsible_id = fields.Many2one(
        "res.users",
        string="Responsible",
        default=lambda self: self.env.user,
    )
    bonus_month = fields.Float(string="Bonus (Month)")
    work_day_of_year = fields.Float(string="Work Day of Year")
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("inprocess", "In Process"),
            ("done", "Done"),
            ("cancel", "Cancel"),
        ],
        string="Status",
        default="draft",
        copy=False,
    )
    company_id = fields.Many2one(
        "res.company",
        string="Company",
        required=True,
        default=lambda self: self.env.company,
    )
    line_ids = fields.One2many(
        "ykk.kpi.bonus.calculate.line",
        "calculate_id",
        string="Lines",
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", "New") == "New":
                vals["name"] = self.env["ir.sequence"].next_by_code("ykk.kpi.bonus.calculate") or "New"
        return super().create(vals_list)

    def action_confirm(self):
        self.write({"state": "inprocess"})

    def action_done(self):
        self.write({"state": "done"})

    def action_cancel(self):
        self.write({"state": "cancel"})

    def action_draft(self):
        self.write({"state": "draft"})

    def action_export_excel(self):
        self.ensure_one()
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {"in_memory": True})
        sheet = workbook.add_worksheet("Bonus")
        bold = workbook.add_format({"bold": True})

        headers = [
            "Employee", "Level", "Department", "Type", "Current Salary",
            "COLA", "POST", "Serv.Year", "Serv.Year Amount", "Day ATT",
            "Bonus", "Grade", "Bonus(GRD)", "Minus Leave / Day",
            "Minus Leave / Amount", "Bonus-Leave", "Net Pay",
        ]
        for col, header in enumerate(headers):
            sheet.write(0, col, header, bold)

        type_labels = {"monthly": "Monthly", "daily": "Daily"}
        row = 1
        for line in self.line_ids:
            values = [
                line.employee_id.display_name or "",
                line.level_id.display_name or "",
                line.department_id.display_name or "",
                type_labels.get(line.employee_type, ""),
                line.current_salary,
                line.cola,
                line.post_amount,
                line.serv_year,
                line.serv_year_amount,
                line.day_att,
                line.bonus,
                line.grade_id.display_name or "",
                line.bonus_grd,
                line.minus_leave_day,
                line.minus_leave_amount,
                line.bonus_leave,
                line.net_pay,
            ]
            for col, value in enumerate(values):
                sheet.write(row, col, value)
            row += 1

        workbook.close()
        output.seek(0)
        safe_name = (self.name or "Bonus Calculate").replace("/", "-")
        filename = "%s.xlsx" % safe_name
        attachment = self.env["ir.attachment"].create({
            "name": filename,
            "type": "binary",
            "datas": base64.b64encode(output.read()),
            "res_model": self._name,
            "res_id": self.id,
            "mimetype": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        })
        return {
            "type": "ir.actions.act_url",
            "url": "/web/content/%s?download=true" % attachment.id,
            "target": "self",
        }


class BonusCalculateLine(models.Model):
    _name = "ykk.kpi.bonus.calculate.line"
    _description = "Bonus Calculate Line"

    calculate_id = fields.Many2one(
        "ykk.kpi.bonus.calculate",
        string="Bonus Calculate",
        required=True,
        ondelete="cascade",
    )
    employee_id = fields.Many2one("hr.employee", string="Employee")

    # default มาตาม Employee (logic เดียวกับ Salary Calculate)
    level_id = fields.Many2one(
        "ykk.kpi.level",
        string="Job Level",
        compute="_compute_from_employee",
        store=True,
        readonly=False,
    )
    department_id = fields.Many2one(
        "hr.department",
        string="Department",
        compute="_compute_from_employee",
        store=True,
        readonly=False,
    )
    employee_type = fields.Selection(
        related="employee_id.ykk_kpi_employee_type",
        string="Type",
        store=True,
    )
    current_salary = fields.Float(
        string="Current Salary",
        compute="_compute_from_employee",
        store=True,
        readonly=False,
    )

    cola = fields.Float(string="COLA")
    post_amount = fields.Float(string="POST")
    serv_year = fields.Float(string="Serv.Year")
    # [(Current Salary + COLA + POST) / 25] * Serv.Year
    serv_year_amount = fields.Float(
        string="Serv.Year Amount",
        compute="_compute_serv_year_amount",
        store=True,
    )
    # default มาจาก Work Day of Year (header) - แก้ไขได้
    day_att = fields.Float(
        string="Day ATT",
        compute="_compute_day_att",
        store=True,
        readonly=False,
    )
    # [(Current Salary + COLA + POST) * Bonus(Month)] / Work Day of Year * Day ATT
    bonus = fields.Float(
        string="Bonus",
        compute="_compute_bonus",
        store=True,
    )
    grade_id = fields.Many2one("ykk.kpi.grade", string="Grade")
    # Bonus * Grade Score (GRD จาก Configuration)
    bonus_grd = fields.Float(
        string="Bonus(GRD)",
        compute="_compute_bonus_grd",
        store=True,
    )
    minus_leave_day = fields.Float(string="Minus Leave / Day")
    # Bonus(GRD) / Day ATT * Minus Leave/Day
    minus_leave_amount = fields.Float(
        string="Minus Leave / Amount",
        compute="_compute_minus_leave_amount",
        store=True,
    )
    # Bonus(GRD) - Minus Leave/Amount
    bonus_leave = fields.Float(
        string="Bonus-Leave",
        compute="_compute_bonus_leave",
        store=True,
    )
    # Serv.Year Amount + Bonus-Leave
    net_pay = fields.Float(
        string="Net Pay",
        compute="_compute_net_pay",
        store=True,
    )

    @api.depends("employee_id")
    def _compute_from_employee(self):
        for line in self:
            employee = line.employee_id
            line.level_id = employee.ykk_kpi_level_id
            line.department_id = employee.department_id
            line.current_salary = employee.ykk_kpi_salary

    @api.depends("calculate_id.work_day_of_year")
    def _compute_day_att(self):
        for line in self:
            line.day_att = line.calculate_id.work_day_of_year

    @api.depends("current_salary", "cola", "post_amount", "serv_year")
    def _compute_serv_year_amount(self):
        for line in self:
            line.serv_year_amount = ((line.current_salary + line.cola + line.post_amount) / 25.0) * line.serv_year

    @api.depends(
        "current_salary",
        "cola",
        "post_amount",
        "day_att",
        "calculate_id.bonus_month",
        "calculate_id.work_day_of_year",
    )
    def _compute_bonus(self):
        for line in self:
            work_day = line.calculate_id.work_day_of_year
            if work_day:
                line.bonus = ((line.current_salary + line.cola + line.post_amount)
                              * line.calculate_id.bonus_month) / work_day * line.day_att
            else:
                line.bonus = 0.0

    @api.depends("bonus", "grade_id.grade_score")
    def _compute_bonus_grd(self):
        for line in self:
            line.bonus_grd = line.bonus * line.grade_id.grade_score

    @api.depends("bonus_grd", "day_att", "minus_leave_day")
    def _compute_minus_leave_amount(self):
        for line in self:
            if line.day_att:
                line.minus_leave_amount = line.bonus_grd / line.day_att * line.minus_leave_day
            else:
                line.minus_leave_amount = 0.0

    @api.depends("bonus_grd", "minus_leave_amount")
    def _compute_bonus_leave(self):
        for line in self:
            line.bonus_leave = line.bonus_grd - line.minus_leave_amount

    @api.depends("serv_year_amount", "bonus_leave")
    def _compute_net_pay(self):
        for line in self:
            line.net_pay = line.serv_year_amount + line.bonus_leave
