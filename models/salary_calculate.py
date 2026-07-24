import base64
import io

import xlsxwriter

from odoo import api, fields, models


class SalaryCalculate(models.Model):
    _name = "ykk.kpi.salary.calculate"
    _description = "Salary Calculate"
    _order = "id desc"

    name = fields.Char(string="Reference", default="New", copy=False, readonly=True)
    period_id = fields.Many2one("ykk.kpi.period", string="Period")
    responsible_id = fields.Many2one(
        "res.users",
        string="Responsible",
        default=lambda self: self.env.user,
    )
    increase_percent = fields.Float(string="Increase new %")
    over_salary_range_percent = fields.Float(string="If over Salary Range %")
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
        "ykk.kpi.salary.calculate.line",
        "calculate_id",
        string="Lines",
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", "New") == "New":
                vals["name"] = self.env["ir.sequence"].next_by_code("ykk.kpi.salary.calculate") or "New"
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
        sheet = workbook.add_worksheet("New Salary")
        bold = workbook.add_format({"bold": True})

        headers = [
            "Employee", "Level", "Department", "Type", "Current Salary",
            "Increase %", "Increase new Salary Year", "Merit%", "Att%",
            "Grade", "+/- Grade", "Cal By Grade", "Cal By Time",
            "Over Leave Day", "Over Leave Baht", "Att",
            "Final Increase Salary", "New Salary", "New Salary Month",
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
                line.effective_increase_percent,
                line.increase_new_salary_year,
                line.merit,
                line.att,
                line.grade_id.display_name or "",
                line.plus_minus,
                line.cal_by_grade,
                line.cal_by_time,
                line.over_leave_day,
                line.over_leave_baht,
                line.att_amount,
                line.increase,
                line.new_salary,
                line.new_salary_month,
            ]
            for col, value in enumerate(values):
                sheet.write(row, col, value)
            row += 1

        workbook.close()
        output.seek(0)
        safe_name = (self.name or "Salary Calculate").replace("/", "-")
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


class SalaryCalculateLine(models.Model):
    _name = "ykk.kpi.salary.calculate.line"
    _description = "Salary Calculate Line"

    calculate_id = fields.Many2one(
        "ykk.kpi.salary.calculate",
        string="Salary Calculate",
        required=True,
        ondelete="cascade",
    )
    employee_id = fields.Many2one("hr.employee", string="Employee")

    # default มาตาม Employee (แก้ไขได้)
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

    # True เมื่อ Current Salary เกิน Max Salary ของ Level
    is_over_range = fields.Boolean(
        string="Over Salary Range",
        compute="_compute_effective_increase_percent",
        store=True,
    )
    # อัตราที่ใช้จริง: ปกติ = Increase new % / ถ้าเกิน Max = If over Salary Range %
    effective_increase_percent = fields.Float(
        string="Increase %",
        compute="_compute_effective_increase_percent",
        store=True,
    )

    # Salary * Increase new %
    increase_new_salary_year = fields.Float(
        string="Increase new Salary Year",
        compute="_compute_increase_new_salary_year",
        store=True,
    )

    # default มาตาม Level (แก้ไขได้) - ค่าเป็น %
    merit = fields.Float(
        string="Merit%",
        compute="_compute_from_level",
        store=True,
        readonly=False,
    )
    att = fields.Float(
        string="Att%",
        compute="_compute_from_level",
        store=True,
        readonly=False,
    )

    grade_id = fields.Many2one("ykk.kpi.grade", string="Grade")

    # Cal By Grade * (+/- ใน Grade)  (แก้ไขไม่ได้)
    plus_minus = fields.Float(
        string="+/- Grade",
        compute="_compute_plus_minus",
        store=True,
    )

    # Increase new Salary Year * Merit %
    cal_by_grade = fields.Float(
        string="Cal By Grade",
        compute="_compute_cal_by_grade",
        store=True,
    )
    # Increase new Salary Year * Att %
    cal_by_time = fields.Float(
        string="Cal By Time",
        compute="_compute_cal_by_time",
        store=True,
    )
    over_leave_day = fields.Float(string="Over Leave Day")
    # (Cal By Time * Over Leave Day) * Increase new % (header)
    over_leave_baht = fields.Float(
        string="Over Leave Baht",
        compute="_compute_over_leave_baht",
        store=True,
    )
    # Cal By Time - Over Leave Baht
    att_amount = fields.Float(
        string="Att",
        compute="_compute_att_amount",
        store=True,
    )
    # Cal By Grade + (+/- Grade) + Att
    increase = fields.Float(
        string="Final Increase Salary",
        compute="_compute_increase",
        store=True,
    )
    new_salary = fields.Float(
        string="New Salary",
        compute="_compute_new_salary",
        store=True,
    )
    new_salary_month = fields.Float(
        string="New Salary Month",
        compute="_compute_new_salary_month",
        store=True,
    )

    @api.depends("employee_id")
    def _compute_from_employee(self):
        for line in self:
            employee = line.employee_id
            line.level_id = employee.ykk_kpi_level_id
            line.department_id = employee.department_id
            line.current_salary = employee.ykk_kpi_salary

    @api.depends("level_id")
    def _compute_from_level(self):
        for line in self:
            line.merit = line.level_id.merit
            line.att = line.level_id.att

    @api.depends("cal_by_grade", "grade_id.plus_minus")
    def _compute_plus_minus(self):
        for line in self:
            line.plus_minus = line.cal_by_grade * line.grade_id.plus_minus

    @api.depends(
        "current_salary",
        "level_id.max_salary",
        "calculate_id.increase_percent",
        "calculate_id.over_salary_range_percent",
    )
    def _compute_effective_increase_percent(self):
        for line in self:
            over = bool(line.level_id.max_salary) and line.current_salary > line.level_id.max_salary
            line.is_over_range = over
            if over:
                line.effective_increase_percent = line.calculate_id.over_salary_range_percent
            else:
                line.effective_increase_percent = line.calculate_id.increase_percent

    @api.depends("current_salary", "effective_increase_percent")
    def _compute_increase_new_salary_year(self):
        for line in self:
            line.increase_new_salary_year = line.current_salary * (line.effective_increase_percent / 100.0)

    @api.depends("increase_new_salary_year", "merit")
    def _compute_cal_by_grade(self):
        for line in self:
            line.cal_by_grade = line.increase_new_salary_year * (line.merit / 100.0)

    @api.depends("increase_new_salary_year", "att")
    def _compute_cal_by_time(self):
        for line in self:
            line.cal_by_time = line.increase_new_salary_year * (line.att / 100.0)

    @api.depends("cal_by_time", "over_leave_day", "effective_increase_percent")
    def _compute_over_leave_baht(self):
        for line in self:
            line.over_leave_baht = (line.cal_by_time * line.over_leave_day) * (line.effective_increase_percent / 100.0)

    @api.depends("cal_by_time", "over_leave_baht")
    def _compute_att_amount(self):
        for line in self:
            line.att_amount = line.cal_by_time - line.over_leave_baht

    @api.depends("cal_by_grade", "plus_minus", "att_amount")
    def _compute_increase(self):
        for line in self:
            line.increase = line.cal_by_grade + line.plus_minus + line.att_amount

    @api.depends("current_salary", "increase")
    def _compute_new_salary(self):
        for line in self:
            line.new_salary = line.current_salary + line.increase

    @api.depends("employee_type", "new_salary", "calculate_id.company_id.ykk_company_working_day")
    def _compute_new_salary_month(self):
        for line in self:
            if line.employee_type == "monthly":
                line.new_salary_month = line.new_salary
            else:
                line.new_salary_month = line.new_salary * line.calculate_id.company_id.ykk_company_working_day
