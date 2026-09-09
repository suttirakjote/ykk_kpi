from odoo import fields, models


class KpiEvaluationRule(models.Model):
    _name = "ykk.kpi.evaluation.rule"
    _description = "Evaluation Rule"
    _rec_name = "user_id"
    _order = "id desc"

    first_evaluator_id = fields.Many2one("res.users", string="First Evaluator")
    second_evaluator_id = fields.Many2one("res.users", string="Second Evaluator")
    user_id = fields.Many2one("res.users", string="Employee")

    company_id = fields.Many2one("res.company", string="Company", required=True, default=lambda self: self.env.company)
    active = fields.Boolean(string="Active", default=True)
