from odoo import fields, models, _

class KpiSequenceSetting(models.Model):
    _name = "ykk.kpi.sequence.setting"
    _description = "KPI Sequence Setting"

    name = fields.Char(string="Name")
    department_id = fields.Many2one("hr.department", string="Department")
    menu = fields.Selection([
        ("template_kpi", "Template KPI"),
        ("annual_kpi", "KPI/Goal Setting"),
        ("department_kpi", "Evaluation")],string="Menu")
    sequence_id = fields.Many2one("ir.sequence", string="Sequence")
    company_id = fields.Many2one("res.company", string="Company", required=True, default=lambda self: self.env.company)
    active = fields.Boolean(string="Active", default=True)
