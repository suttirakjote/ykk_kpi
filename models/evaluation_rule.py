from odoo import api, fields, models


class KpiEvaluationRule(models.Model):
    _name = "ykk.kpi.evaluation.rule"
    _description = "Evaluation Rule"
    _rec_name = "user_id"
    _order = "id desc"

    first_evaluator_id = fields.Many2one("res.users", string="First Evaluator")
    second_evaluator_id = fields.Many2one("res.users", string="Second Evaluator")
    user_id = fields.Many2one("res.users", string="Employee")
    rule_type = fields.Selection([
        ("employee", "Employee"),
        ("department", "Department")], string="Rule Type", default="employee")
    department_id = fields.Many2one("hr.department", string="Department")

    company_id = fields.Many2one("res.company", string="Company", required=True, default=lambda self: self.env.company)
    active = fields.Boolean(string="Active", default=True)

    @api.onchange("rule_type")
    def _onchange_rule_type(self):
        for rule in self:
            if rule.rule_type == "employee":
                rule.department_id = False
            elif rule.rule_type == "department":
                rule.user_id = False


class ResUsers(models.Model):
    _inherit = "res.users"

    evaluation_rule_ids = fields.One2many(
        "ykk.kpi.evaluation.rule",
        "user_id",
        string="Evaluation Rules",
    )
