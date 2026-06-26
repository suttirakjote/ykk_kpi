from odoo import api, fields, models
from odoo.exceptions import ValidationError


class KpiPeriod(models.Model):
    _name = "ykk.kpi.period"
    _description = "KPI Period"
    _order = "id desc"

    name = fields.Char(string="Name", required=True)
    is_end_period = fields.Boolean(string="End Period")
    period_type = fields.Selection([
        ("month", "Month"),
        ("quarter", "Quarter"),
        ("half_year", "Half Year"),
        ("year", "Year")], string="Period Type", required=True)
    start_date = fields.Date(string="Start Date", required=True)
    end_date = fields.Date(string="End Date", required=True)
    company_id = fields.Many2one("res.company", string="Company", required=True, default=lambda self: self.env.company)
    active = fields.Boolean(string="Active", default=True)

    _sql_constraints = [
        ("name_company_unique", "unique(name, company_id)", "The period name must be unique per company."),
    ]

    @api.constrains("start_date", "end_date")
    def _check_date_range(self):
        for record in self:
            if record.start_date and record.end_date and record.start_date > record.end_date:
                raise ValidationError("Start Date must be less than or equal to End Date.")
