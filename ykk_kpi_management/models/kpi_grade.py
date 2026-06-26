from odoo import api, fields, models
from odoo.exceptions import ValidationError


class KpiGrade(models.Model):
    _name = "ykk.kpi.grade"
    _description = "KPI Grade Configuration"
    _order = "id desc"

    name = fields.Char(string="Name", required=True)
    code = fields.Char(string="Code", required=True)
    start_score = fields.Float(string="Start Score", required=True)
    end_score = fields.Float(string="End Score", required=True)
    description = fields.Text(string="Description")
    company_id = fields.Many2one("res.company", string="Company", required=True, default=lambda self: self.env.company)
    active = fields.Boolean(string="Active", default=True)

    plus_minus = fields.Float(string="+/-")
    grade_score = fields.Float(string="Grade Score")

    _sql_constraints = [
        ("name_company_unique", "unique(name, company_id)", "The name must be unique per company."),
    ]

    @api.constrains("start_score", "end_score")
    def _check_score_range(self):
        for record in self:
            if record.start_score > record.end_score:
                raise ValidationError("Start Score must be less than or equal to End Score.")
