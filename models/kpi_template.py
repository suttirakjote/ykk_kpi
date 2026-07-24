from odoo import api, fields, models
from odoo.exceptions import ValidationError

class KpiTemplate(models.Model):
    _name = "ykk.kpi.template"
    _description = "Template KPI"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "id desc"

    name = fields.Char(string="Name", default="New", required=True, readonly=True, copy=False)
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
    active = fields.Boolean(string="Active", default=True)
    performance_line_ids = fields.One2many("ykk.kpi.template.performance.line", "template_id", string="Performance Evaluation", copy=True)
    employee_ids = fields.Many2many("hr.employee", string="Employees")
    # ฟิลด์ช่วย: เลือกหลาย Goal พร้อมกัน แล้วระบบสร้างบรรทัดแยกให้ goal ละ 1 บรรทัด
    goal_select_ids = fields.Many2many(
        "ykk.kpi.goal",
        "ykk_kpi_template_goal_select_rel",
        "template_id",
        "goal_id",
        string="Add Goals",
        copy=False,
    )

    @api.onchange("goal_select_ids")
    def _onchange_goal_select_ids(self):
        if not self.goal_select_ids:
            return
        Line = self.env["ykk.kpi.template.performance.line"]
        existing = self.performance_line_ids.mapped("goal_id")
        for goal in self.goal_select_ids:
            if goal not in existing:
                self.performance_line_ids |= Line.new({"goal_id": goal.id})
        # เคลียร์ฟิลด์ช่วยหลังเพิ่มบรรทัดแล้ว
        self.goal_select_ids = [(5, 0, 0)]

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
    criteria_details = fields.Text(string="Criteria Details")
    weight = fields.Float(string="Weight")
