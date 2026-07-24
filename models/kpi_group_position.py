from odoo import fields, models


class KpiGroupPosition(models.Model):
    _name = "ykk.kpi.group.position"
    _description = "KPI Group Position"
    _order = "id desc"

    name = fields.Char(string="Name", required=True)
    company_id = fields.Many2one("res.company", string="Company", required=True, default=lambda self: self.env.company)
    active = fields.Boolean(string="Active", default=True)

    _sql_constraints = [
        ("name_company_unique", "unique(name, company_id)", "The name must be unique per company."),
    ]
