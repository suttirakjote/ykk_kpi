from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    ykk_company_working_day = fields.Float(string="Company Working Day", default=22.0)


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    ykk_company_working_day = fields.Float(
        related="company_id.ykk_company_working_day",
        string="Company Working Day",
        readonly=False,
    )
