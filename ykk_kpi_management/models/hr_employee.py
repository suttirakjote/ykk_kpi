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

    @api.depends("ykk_employee_code", "name")
    def _compute_display_name(self):
        super()._compute_display_name()
        for employee in self:
            if employee.ykk_employee_code and employee.display_name:
                employee.display_name = "[%s] %s" % (employee.ykk_employee_code, employee.display_name)
