from odoo import api, fields, models


class KpiHrEvaluation(models.Model):
    _name = "ykk.kpi.hr.evaluation"
    _description = "Human Resource Evaluation"
    _order = "id desc"
    _rec_names_search = ["code", "name"]

    code = fields.Char(string="Code", required=True)
    name = fields.Char(string="Name", required=True)
    achievement_criteria = fields.Text(string="Achievement Criteria")
    criteria_details = fields.Text(string="Criteria Details")
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
    description = fields.Text(string="Description")
    company_id = fields.Many2one(
        "res.company",
        string="Company",
        required=True,
        default=lambda self: self.env.company,
    )
    active = fields.Boolean(string="Active", default=True)

    _sql_constraints = [
        ("code_company_unique", "unique(code, company_id)", "The code must be unique per company."),
    ]

    @api.depends("code", "name")
    def _compute_display_name(self):
        """แสดงเป็น [Code] Name ทุกที่ที่อ้างถึง HR Evaluation"""
        for record in self:
            record.display_name = "[%s] %s" % (record.code, record.name) if record.code else record.name
