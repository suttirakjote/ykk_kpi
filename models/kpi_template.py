from odoo import api, fields, models
from odoo.exceptions import ValidationError

class KpiTemplate(models.Model):
    _name = "ykk.kpi.template"
    _description = "Template KPI"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "id desc"

    name = fields.Char(string="Name", default="New", required=True, readonly=True)
    level_id = fields.Many2one("ykk.kpi.level", string="Job Level", required=True, tracking=True)
    department_id = fields.Many2one("hr.department", string="Department", required=True, tracking=True)
    remark = fields.Text(string="Remark", tracking=True)
    state = fields.Selection([
            ("draft", "Draft"),
            ("done", "Done"),
            ("cancel", "Cancel")], string="Status", default="draft", required=True, tracking=True)
    responsible_id = fields.Many2one("res.users", string="Responsible", default=lambda self: self.env.user)
    date = fields.Date(string='Date', default=fields.Date.context_today)
    company_id = fields.Many2one("res.company", string="Company", required=True, default=lambda self: self.env.company)
    performance_line_ids = fields.One2many("ykk.kpi.template.performance.line", "template_id", string="Performance Evaluation")
    employee_ids = fields.Many2many("hr.employee", string="Employees")

    def action_done(self):
        self.write({"state": "done"})

    def action_cancel(self):
        self.write({"state": "cancel"})

    def action_draft(self):
        self.write({"state": "draft"})

class KpiTemplatePerformanceLine(models.Model):
    _name = "ykk.kpi.template.performance.line"
    _description = "KPI Template Performance Evaluation Line"

    template_id = fields.Many2one("ykk.kpi.template", string="KPI Template", required=True, ondelete="cascade")
    goal_id = fields.Many2one("ykk.kpi.goal", string="Goal", required=True)
    achievement_criteria = fields.Text(string="Achievement Criteria")
    weight = fields.Float(string="Weight")
