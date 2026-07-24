from odoo import api, fields, models


class HrEmployee(models.Model):
    _inherit = "hr.employee"

    ykk_employee_code = fields.Char(string="Employee Code")
    ykk_kpi_salary = fields.Float(string="Salary")
    ykk_kpi_level_id = fields.Many2one("ykk.kpi.level",string="Job Level")
    ykk_kpi_group_position_id = fields.Many2one("ykk.kpi.group.position", string="Group Position")
    ykk_kpi_employee_type = fields.Selection([
            ("monthly", "Monthly"),
            ("daily", "Daily")], string="Employee Type")
    ykk_start_work_date = fields.Date(string="Start Work Date")
    ykk_age = fields.Char(string="Age", compute="_compute_ykk_age")
    ykk_salary_month = fields.Float(string="Salary/Month", compute="_compute_ykk_salary_month", store=True)
    ykk_kpi_history_ids = fields.One2many("ykk.kpi.employee.history", "employee_id", string="KPI History")

    @api.depends("birthday")
    def _compute_ykk_age(self):
        today = fields.Date.context_today(self)
        for employee in self:
            if employee.birthday:
                years = today.year - employee.birthday.year
                months = today.month - employee.birthday.month
                if today.day < employee.birthday.day:
                    months -= 1
                if months < 0:
                    years -= 1
                    months += 12
                employee.ykk_age = "%d ปี %d เดือน" % (years, months)
            else:
                employee.ykk_age = ""

    @api.depends("ykk_kpi_salary", "ykk_kpi_employee_type")
    def _compute_ykk_salary_month(self):
        for employee in self:
            if employee.ykk_kpi_employee_type == "daily":
                employee.ykk_salary_month = employee.ykk_kpi_salary * 22
            else:
                employee.ykk_salary_month = employee.ykk_kpi_salary

    @api.depends("ykk_employee_code", "name")
    def _compute_display_name(self):
        super()._compute_display_name()
        for employee in self:
            if employee.ykk_employee_code and employee.display_name:
                employee.display_name = "[%s] %s" % (employee.ykk_employee_code, employee.display_name)
