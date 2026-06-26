from odoo import fields, models


class KpiGrade(models.Model):
    _inherit = "ykk.kpi.grade"

    adjustment_score = fields.Float(string="Adjustment Score")
