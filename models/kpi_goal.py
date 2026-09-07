from odoo import api, fields, models

class KpiGoal(models.Model):
    _name = "ykk.kpi.goal"
    _description = "KPI Goal Configuration"
    _order = "id desc"
    _rec_names_search = ["code", "name"]

    code = fields.Char(string="Code", required=True)
    name = fields.Char(string="Name", required=True)
    achievement_criteria = fields.Text(string="Achievement Criteria")
    criteria_details = fields.Text(string="Criteria Details")
    group_type = fields.Selection([
            ("individual", "Individual"),
            ("section", "Section")], string="Group Type")
    type = fields.Selection([("performance", "Performance Evaluation")], string="Type", default="performance",required=True)
    department_id = fields.Many2one("hr.department", string="Department")
    description = fields.Text(string="Description")
    company_id = fields.Many2one("res.company", string="Company", required=True, default=lambda self: self.env.company)
    active = fields.Boolean(string="Active", default=True)

    _sql_constraints = [
        ("code_company_unique", "unique(code, company_id)", "The code must be unique per company."),
    ]

    @api.depends("code", "name")
    def _compute_display_name(self):
        """แสดงเป็น [Code] Name ทุกที่ที่อ้างถึง Goal"""
        for record in self:
            record.display_name = "[%s] %s" % (record.code, record.name) if record.code else record.name
