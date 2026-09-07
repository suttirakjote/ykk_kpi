from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools import float_compare


class KpiAnnualKpi(models.Model):
    _name = "ykk.kpi.annual.kpi"
    _description = "KPI/Goal Setting"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = "id desc"

    name = fields.Char(string="Name", default='New', required=True, readonly=True)
    state = fields.Selection([
            ("draft", "Draft"),
            ("inprocess", "Inprocess"),
            ("done", "Done"),
            ("cancel", "Cancel")], string="Status", default="draft", required=True, tracking=True)
    employee_id = fields.Many2one("hr.employee", string="Employee", required=True, tracking=True)
    group_position_id = fields.Many2one("ykk.kpi.group.position", string="Group Position", compute="_compute_employee_info", store=True, readonly=True, tracking=True)
    level_id = fields.Many2one("ykk.kpi.level", string="Job Level", compute="_compute_employee_info", store=True, readonly=True, tracking=True)
    department_id = fields.Many2one("hr.department", string="Department", compute="_compute_employee_info", store=True, readonly=True, tracking=True)
    period_id = fields.Many2one("ykk.kpi.period", string="Period", required=True, tracking=True)
    responsible_id = fields.Many2one("res.users", string="Responsible", default=lambda self: self.env.user)
    date = fields.Date(string='Date', default=fields.Date.context_today)
    company_id = fields.Many2one("res.company", string="Company", required=True, default=lambda self: self.env.company)

    performance_line_ids = fields.One2many("ykk.kpi.annual.kpi.performance.line", "annual_kpi_id", string="Performance Evaluation")
    role_line_ids = fields.One2many("ykk.kpi.annual.kpi.role.line", "annual_kpi_id", string="Role-based Behavior Evaluation")
    behavior_line_ids = fields.One2many("ykk.kpi.annual.kpi.behavior.line", "annual_kpi_id", string="Behavior Evaluation")
    attitude_line_ids = fields.One2many("ykk.kpi.annual.kpi.attitude.line", "annual_kpi_id", string="Attitude Evaluation")

    performance_weight = fields.Integer(string="Performance Evaluation", tracking=True)
    indicator_weight = fields.Integer(string="Indicator Weight (%)", tracking=True)
    role_based_behavior_weight = fields.Integer(string="Role-based Behavior Evaluation", tracking=True)
    behavior_weight = fields.Integer(string="Behavior Evaluation", tracking=True)
    attitude_weight = fields.Integer(string="Attitude Evaluation", tracking=True)
    weight_total = fields.Integer(string="Sum %", compute="_compute_weight_total")
    group_kpi_user = fields.Boolean(compute="_compute_group_kpi_user")

    template_id = fields.Many2one("ykk.kpi.template", string="KPI Template")

    @api.depends_context("uid")
    def _compute_group_kpi_user(self):
        user = self.env.user
        readonly_user = (
            user.has_group("ykk_kpi.group_ykk_kpi_user")
            and not user.has_group("ykk_kpi.group_ykk_kpi_admin")
        )
        for record in self:
            record.group_kpi_user = readonly_user

    @api.depends("performance_weight", "role_based_behavior_weight",
                 "behavior_weight", "attitude_weight")
    def _compute_weight_total(self):
        for record in self:
            record.weight_total = (
                record.performance_weight + record.role_based_behavior_weight
                + record.behavior_weight + record.attitude_weight
            )

    @api.depends("employee_id")
    def _compute_employee_info(self):
        for record in self:
            record.group_position_id = record.employee_id.ykk_kpi_group_position_id
            record.level_id = record.employee_id.ykk_kpi_level_id
            record.department_id = record.employee_id.department_id

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if "indicator_weight" not in vals and vals.get("employee_id"):
                employee = self.env["hr.employee"].browse(vals["employee_id"])
                vals["indicator_weight"] = (
                    employee.ykk_kpi_level_id.indicator_weight
                )
        return super().create(vals_list)

    @api.onchange("employee_id")
    def _onchange_employee_id(self):
        for record in self:
            if record.employee_id:
                record.indicator_weight = (
                    record.employee_id.ykk_kpi_level_id.indicator_weight
                )
                template = self.env["ykk.kpi.template"].search(
                    [
                        ("employee_ids", "in", record.employee_id.id),
                        ("department_id", "=", record.employee_id.department_id.id),
                        ("level_id", "=", record.employee_id.ykk_kpi_level_id.id),
                        ("state", "=", 'done'),
                    ],
                    order="id desc",
                    limit=1,
                )
                record.template_id = template
                record._set_performance_lines_from_template(template)
                record._set_role_lines_from_hr_evaluation()
                record._set_behavior_lines_from_hr_evaluation()
                record._set_attitude_lines_from_hr_evaluation()
            else:
                record.indicator_weight = 0
                record.template_id = False
                record._set_performance_lines_from_template(False)
                record._set_role_lines_from_hr_evaluation()
                record._set_behavior_lines_from_hr_evaluation()
                record._set_attitude_lines_from_hr_evaluation()

    def _set_performance_lines_from_template(self, template):
        """Replace performance lines with the selected KPI template lines."""
        for record in self:
            performance_line_commands = [(5, 0, 0)]
            if template:
                performance_line_commands.extend([
                    (0, 0, {
                        "goal_id": line.goal_id.id,
                        "achievement_criteria": line.achievement_criteria,
                        "criteria_details": line.criteria_details,
                        "weight": line.weight,
                    })
                    for line in template.performance_line_ids
                ])
            record.performance_line_ids = performance_line_commands

    def _set_role_lines_from_hr_evaluation(self):
        """Replace role lines with matching role-based HR evaluation names."""
        for record in self:
            role_line_commands = [(5, 0, 0)]
            if record.employee_id:
                evaluations = self.env["ykk.kpi.hr.evaluation"].search(
                    [
                        ("type", "=", "role_based_behavior"),
                        "|",
                        ("department_id", "=", record.employee_id.department_id.id),
                        ("department_id", "=", False),
                    ],
                    order="id desc",
                )
                role_line_commands.extend([
                    (0, 0, {
                        "name": evaluation.display_name,
                        "achievement_criteria": evaluation.achievement_criteria,
                        "criteria_details": evaluation.criteria_details,
                    })
                    for evaluation in evaluations
                ])
            record.role_line_ids = role_line_commands

    def _set_behavior_lines_from_hr_evaluation(self):
        """Replace behavior lines with matching behavior HR evaluation names."""
        for record in self:
            behavior_line_commands = [(5, 0, 0)]
            if record.employee_id:
                evaluations = self.env["ykk.kpi.hr.evaluation"].search(
                    [
                        ("type", "=", "behavior"),
                        "|",
                        ("department_id", "=", record.employee_id.department_id.id),
                        ("department_id", "=", False),
                    ],
                    order="id desc",
                )
                behavior_line_commands.extend([
                    (0, 0, {
                        "name": evaluation.display_name,
                        "achievement_criteria": evaluation.achievement_criteria,
                        "criteria_details": evaluation.criteria_details,
                    })
                    for evaluation in evaluations
                ])
            record.behavior_line_ids = behavior_line_commands

    def _set_attitude_lines_from_hr_evaluation(self):
        """Replace attitude lines with matching attitude HR evaluation names."""
        for record in self:
            attitude_line_commands = [(5, 0, 0)]
            if record.employee_id:
                evaluations = self.env["ykk.kpi.hr.evaluation"].search(
                    [
                        ("type", "=", "attitude"),
                        "|",
                        ("department_id", "=", record.employee_id.department_id.id),
                        ("department_id", "=", False),
                    ],
                    order="id desc",
                )
                attitude_line_commands.extend([
                    (0, 0, {
                        "name": evaluation.display_name,
                        "achievement_criteria": evaluation.achievement_criteria,
                        "criteria_details": evaluation.criteria_details,
                    })
                    for evaluation in evaluations
                ])
            record.attitude_line_ids = attitude_line_commands
    
    def action_inprocess(self):
        self.write({"state": "inprocess"})

    def action_done(self):
        for record in self:
            errors = []
            if record.weight_total != 100:
                errors.append(_("Indicator Weight = %s%%") % record.weight_total)
            tabs = [
                (_("Performance Evaluation"), record.performance_line_ids),
                (_("Role-based Behavior Evaluation"), record.role_line_ids),
                (_("Behavior Evaluation"), record.behavior_line_ids),
                (_("Attitude Evaluation"), record.attitude_line_ids),
            ]
            for tab_name, lines in tabs:
                if lines and abs(sum(lines.mapped("weight")) - 100.0) > 0.01:
                    errors.append("%s = %s%%" % (tab_name, sum(lines.mapped("weight"))))
            if errors:
                raise ValidationError(
                    _("Weight ต้องเท่ากับ 100%% ก่อนกด Done:\n- %s") % "\n- ".join(errors)
                )
        self.write({"state": "done"})

    def action_cancel(self):
        self.write({"state": "cancel"})

    def action_draft(self):
        self.write({"state": "draft"})

class KpiAnnualKpiPerformanceLine(models.Model):
    _name = "ykk.kpi.annual.kpi.performance.line"
    _description = "KPI/Goal Setting Performance Evaluation Line"

    annual_kpi_id = fields.Many2one("ykk.kpi.annual.kpi", string="KPI/Goal Setting", required=True, ondelete="cascade")
    goal_id = fields.Many2one("ykk.kpi.goal", string="Goal", required=True)
    achievement_criteria = fields.Text(string="Achievement Criteria")
    criteria_details = fields.Text(string="Criteria Details")
    weight = fields.Float(string="Weight")

    def action_view_goal(self):
        self.ensure_one()
        if not self.goal_id:
            return False

        return {
            "type": "ir.actions.act_window",
            "name": _("Goal"),
            "res_model": "ykk.kpi.goal",
            "res_id": self.goal_id.id,
            "view_mode": "form",
            "views": [
                (
                    self.env.ref("ykk_kpi.view_ykk_kpi_goal_form").id,
                    "form",
                )
            ],
            "target": "current",
            "context": {
                **self.env.context,
                "create": False,
                "edit": False,
                "delete": False,
                "form_view_initial_mode": "readonly",
            },
        }


class KpiAnnualKpiRoleLine(models.Model):
    _name = "ykk.kpi.annual.kpi.role.line"
    _description = "KPI/Goal Setting Role-based Behavior Evaluation Line"

    annual_kpi_id = fields.Many2one("ykk.kpi.annual.kpi", string="KPI/Goal Setting", required=True, ondelete="cascade")
    name = fields.Char(string="Goal", required=True)
    achievement_criteria = fields.Text(string="Achievement Criteria")
    criteria_details = fields.Text(string="Criteria Details")
    weight = fields.Float(string="Weight")


class KpiAnnualKpiBehaviorLine(models.Model):
    _name = "ykk.kpi.annual.kpi.behavior.line"
    _description = "KPI/Goal Setting Behavior Evaluation Line"

    annual_kpi_id = fields.Many2one("ykk.kpi.annual.kpi", string="KPI/Goal Setting", required=True, ondelete="cascade")
    name = fields.Char(string="Goal", required=True)
    achievement_criteria = fields.Text(string="Achievement Criteria")
    criteria_details = fields.Text(string="Criteria Details")
    weight = fields.Float(string="Weight")


class KpiAnnualKpiAttitudeLine(models.Model):
    _name = "ykk.kpi.annual.kpi.attitude.line"
    _description = "KPI/Goal Setting Attitude Evaluation Line"

    annual_kpi_id = fields.Many2one("ykk.kpi.annual.kpi", string="KPI/Goal Setting", required=True, ondelete="cascade")
    name = fields.Char(string="Goal", required=True)
    achievement_criteria = fields.Text(string="Achievement Criteria")
    criteria_details = fields.Text(string="Criteria Details")
    weight = fields.Float(string="Weight")
