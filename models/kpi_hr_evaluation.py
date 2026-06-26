from odoo import fields, models


class KpiHrEvaluation(models.Model):
    _name = "ykk.kpi.hr.evaluation"
    _description = "Human Resource Evaluation"
    _order = "id desc"

    code = fields.Char(string="Code", required=True)
    name = fields.Char(string="Name", required=True)
    group_type = fields.Selection([
        ("individual", "Individual"),
        ("section", "Section"),
    ], string="Group Type")
    type = fields.Selection([
        ("role_based_behavior", "Role-based Behavior Evaluation"),
        ("behavior", "Behavior Evaluation"),
        ("attitude", "Attitude Evaluation"),
    ], string="Type", required=True)
    department_id = fields.Many2one("hr.department", string="Department")
    company_id = fields.Many2one(
        "res.company",
        string="Company",
        required=True,
        default=lambda self: self.env.company,
    )
    active = fields.Boolean(string="Active", default=True)

    _sql_constraints = [
        ("code_company_unique", "unique(code, company_id)", "The code must be unique per company."),
        ("name_company_unique", "unique(name, company_id)", "The name must be unique per company."),
    ]
