from odoo import api, models


class KpiTemplate(models.Model):
    _inherit = "ykk.kpi.template"

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", "New") == "New":
                vals["name"] = self.env["ir.sequence"].next_by_code("ykk.kpi.template") or "New"
        return super().create(vals_list)


class KpiAnnualKpi(models.Model):
    _inherit = "ykk.kpi.annual.kpi"

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", "New") == "New":
                vals["name"] = self.env["ir.sequence"].next_by_code("ykk.kpi.annual.kpi") or "New"
        return super().create(vals_list)
