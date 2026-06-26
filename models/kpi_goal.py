from odoo import fields, models

class KpiGoal(models.Model):
    _name = "ykk.kpi.goal"
    _description = "KPI Goal Configuration"
    _order = "id desc"

    code = fields.Char(string="Code", required=True)
    name = fields.Char(string="Name", required=True)
    group_type = fields.Selection([
            ("individual", "Individual"),
            ("section", "Section")], string="Group Type")
    type = fields.Selection([("performance", "Performance Evaluation")], string="Type", default="performance",required=True)
    department_id = fields.Many2one("hr.department", string="Department")
    company_id = fields.Many2one("res.company", string="Company", required=True, default=lambda self: self.env.company)
    active = fields.Boolean(string="Active", default=True)

    _sql_constraints = [
        ("code_company_unique", "unique(code, company_id)", "The code must be unique per company."),
        ("name_company_unique", "unique(name, company_id)", "The name must be unique per company."),
    ]
