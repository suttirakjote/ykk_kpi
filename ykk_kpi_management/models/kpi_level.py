from odoo import fields, models, api, _

class KpiLevel(models.Model):
    _name = "ykk.kpi.level"
    _description = "KPI Level"
    _order = "id desc"

    name = fields.Char(string="Name", required=True)
    description = fields.Text(string="Description")
    company_id = fields.Many2one("res.company", string="Company", required=True, default=lambda self: self.env.company)
    active = fields.Boolean(string="Active", default=True)

    group_position_id = fields.Many2one("ykk.kpi.group.position", string="Group Job")
    merit = fields.Float(string="Merit")
    att = fields.Float(string="Att.")
    min_salary = fields.Float(string="Min Salary")
    max_salary = fields.Float(string="Max Salary")

    _sql_constraints = [
        ("name_company_unique", "unique(name, company_id)", "The name must be unique per company."),
    ]

    @api.constrains("min_salary", "max_salary")
    def _check_salary_range(self):
        for record in self:
            if (record.min_salary or record.max_salary) and record.max_salary <= record.min_salary:
                raise ValidationError("Max Salary must be greater than Min Salary.")

    @api.constrains("merit", "att")
    def _check_merit_att_percent(self):
        for record in self:
            if (record.merit or record.att) and abs((record.merit + record.att) - 100.0) > 0.01:
                raise ValidationError("Merit % and Att % must add up to 100%.")
