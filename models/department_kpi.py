from odoo import _, api, fields, models
from odoo.exceptions import AccessError, ValidationError, UserError

class KpiDepartmentKpi(models.Model):
    _name = "ykk.kpi.department.kpi"
    _description = "Evaluation"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = "id desc"

    name = fields.Char(string="Name", default='New', required=True, readonly=True)
    state = fields.Selection(
        [
            ("draft", "Self Evaluate"),
            ("inprocess", "1st Evaluate"),
            ("evaluated", "2nd Evaluate"),
            ("approved", "Approved"),
            ("cancel", "Cancel"),
        ],
        string="Status",
        default="draft",
        required=True,
        tracking=True,
    )
    employee_id = fields.Many2one("hr.employee", string="Employee", required=True, tracking=True)
    group_position_id = fields.Many2one("ykk.kpi.group.position", string="Group Position", compute="_compute_employee_info", store=True, readonly=True, tracking=True)
    level_id = fields.Many2one("ykk.kpi.level", string="Job Level", compute="_compute_employee_info", store=True, readonly=True, tracking=True)
    department_id = fields.Many2one("hr.department", string="Department", compute="_compute_employee_info", store=True, readonly=True, tracking=True)
    period_id = fields.Many2one("ykk.kpi.period", string="Period", required=True, tracking=True)
    responsible_id = fields.Many2one("res.users", string="Responsible", default=lambda self: self.env.user)
    date = fields.Date(string='Date', default=fields.Date.context_today)
    annual_id = fields.Many2one("ykk.kpi.annual.kpi", string="KPI/Goal Setting")
    performance_line_ids = fields.One2many("ykk.kpi.department.kpi.performance.line", "department_kpi_id", string="Performance Evaluation")
    role_line_ids = fields.One2many("ykk.kpi.department.kpi.role.line", "department_kpi_id", string="Role-based Behavior Evaluation")
    behavior_line_ids = fields.One2many("ykk.kpi.department.kpi.behavior.line", "department_kpi_id", string="Behavior Evaluation")
    attitude_line_ids = fields.One2many("ykk.kpi.department.kpi.attitude.line", "department_kpi_id", string="Attitude Evaluation")
    total_score = fields.Float(string="Total", digits="KPI Score", compute="_compute_total_score", store=True)
    performance_tab_total = fields.Float(string="Performance Total", digits="KPI Score", compute="_compute_tab_totals")
    role_tab_total = fields.Float(string="Role-based Behavior Total", digits="KPI Score", compute="_compute_tab_totals")
    behavior_tab_total = fields.Float(string="Behavior Total", digits="KPI Score", compute="_compute_tab_totals")
    attitude_tab_total = fields.Float(string="Attitude Total", digits="KPI Score", compute="_compute_tab_totals")
    period_score = fields.Integer(string="Period Score", compute="_compute_period_grade")
    period_grade_id = fields.Many2one("ykk.kpi.grade", string="Period Grade", compute="_compute_period_grade")
    summary_parent_kpi_ids = fields.One2many(
        "ykk.kpi.department.kpi.summary.line",
        "department_kpi_id",
        string="Parent KPIs",
    )
    overall_score = fields.Integer(string="Overall Score", compute="_compute_overall_grade")
    overall_grade_id = fields.Many2one("ykk.kpi.grade", string="Overall Grade", compute="_compute_overall_grade")
    company_id = fields.Many2one("res.company", string="Company", required=True, default=lambda self: self.env.company)
    group_kpi_user = fields.Boolean(compute="_compute_group_kpi_user")
    can_edit_employee = fields.Boolean(compute="_compute_evaluation_permissions")
    can_edit_first_evaluator = fields.Boolean(compute="_compute_evaluation_permissions")
    can_edit_second_evaluator = fields.Boolean(compute="_compute_evaluation_permissions")

    # Indicator Weight (read-only) ดึงจาก KPI/Goal Setting ที่อ้างอิง - แสดงใน tab Summary
    performance_weight = fields.Integer(related="annual_id.performance_weight", string="Performance Evaluation", readonly=True)
    role_based_behavior_weight = fields.Integer(related="annual_id.role_based_behavior_weight", string="Role-based Behavior Evaluation", readonly=True)
    behavior_weight = fields.Integer(related="annual_id.behavior_weight", string="Behavior Evaluation", readonly=True)
    attitude_weight = fields.Integer(related="annual_id.attitude_weight", string="Attitude Evaluation", readonly=True)

    description = fields.Html(string='Description', sanitize_attributes=False)

    @api.depends_context("uid")
    def _compute_group_kpi_user(self):
        user = self.env.user
        readonly_user = (
            user.has_group("ykk_kpi.group_ykk_kpi_user")
            and not user.has_group("ykk_kpi.group_ykk_kpi_admin")
        )
        for record in self:
            record.group_kpi_user = readonly_user

    @api.depends("employee_id.user_id", "company_id")
    @api.depends_context("uid")
    def _compute_evaluation_permissions(self):
        current_user = self.env.user
        for record in self:
            rule = record._get_evaluation_rule()
            record.can_edit_employee = bool(rule and rule.user_id == current_user)
            record.can_edit_first_evaluator = bool(rule and rule.first_evaluator_id == current_user)
            record.can_edit_second_evaluator = bool(rule and rule.second_evaluator_id == current_user)

    @api.model
    def _validate_unique_employee_period(self, employee_id, period_id):
        if not employee_id or not period_id:
            return
        duplicate = self.search([("employee_id", "=", employee_id), ("period_id", "=", period_id)], limit=1)
        if duplicate:
            raise ValidationError(
                _(
                    "The document cannot be created because the Employee and Period "
                    "already exist in document number %s."
                )
                % duplicate.display_name
            )

    @api.depends(
        "performance_line_ids", 
        "performance_line_ids.total_score",
        "role_line_ids", 
        "role_line_ids.total_score",
        "behavior_line_ids",
        "behavior_line_ids.total_score",
        "attitude_line_ids",
        "attitude_line_ids.total_score",)
    def _compute_total_score(self):
        for record in self:
            total_performance = sum(record.performance_line_ids.mapped("total_score"))
            total_role = sum(record.role_line_ids.mapped("total_score"))
            total_behavior = sum(record.behavior_line_ids.mapped("total_score"))
            total_attitude = sum(record.attitude_line_ids.mapped("total_score"))
            record.total_score = total_performance + total_role + total_behavior + total_attitude

    @api.depends(
        "performance_line_ids.total_score",
        "role_line_ids.total_score",
        "behavior_line_ids.total_score",
        "attitude_line_ids.total_score",
    )
    def _compute_tab_totals(self):
        for record in self:
            record.performance_tab_total = sum(record.performance_line_ids.mapped("total_score"))
            record.role_tab_total = sum(record.role_line_ids.mapped("total_score"))
            record.behavior_tab_total = sum(record.behavior_line_ids.mapped("total_score"))
            record.attitude_tab_total = sum(record.attitude_line_ids.mapped("total_score"))

    @api.depends("employee_id")
    def _compute_employee_info(self):
        for record in self:
            record.group_position_id = record.employee_id.ykk_kpi_group_position_id
            record.level_id = record.employee_id.ykk_kpi_level_id
            record.department_id = record.employee_id.department_id

    def action_confirm(self):
        self._check_evaluation_rule()
        rule_id = self._get_evaluation_rule()
        if rule_id.first_evaluator_id != self.env.user:
            raise UserError(
                _("You do not have permission as the First Evaluator.")
            )
        # Update State and Activity
        self.activity_update()
        self.write({"state": "inprocess"})
        self.action_second_evaluate_activity()

    def action_done(self):
        for record in self:
            errors = []
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
        # Update State and Activity
        self._check_evaluation_rule()
        rule_id = self._get_evaluation_rule()
        if rule_id.second_evaluator_id != self.env.user:
            raise UserError(
                _("You do not have permission as the Second Evaluator.")
            )
        self.activity_update()
        self.write({"state": "evaluated"})

    def action_approve(self):
        records_to_approve = self.filtered(lambda record: record.state == "evaluated")
        updated_count = len(records_to_approve)
        skipped_count = len(self) - updated_count
        if records_to_approve:
            records_to_approve.write({"state": "approved"})
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Select Approve Summary"),
                "message": _(
                    "Updated successfully: %(updated)s record(s).\n"
                    "Skipped: %(skipped)s record(s).",
                    updated=updated_count,
                    skipped=skipped_count,
                ),
                "type": "success" if not skipped_count else "warning",
                "sticky": False,
                "next": {
                    "type": "ir.actions.client",
                    "tag": "soft_reload",
                },
            },
        }

    def action_cancel(self):
        self.write({"state": "cancel"})
        self.activity_update()

    def action_draft(self):
        self.write({"state": "draft"})

    def _get_evaluation_rule(self):
        self.ensure_one()
        employee_user = self.employee_id.user_id
        if not employee_user:
            return self.env["ykk.kpi.evaluation.rule"]

        return self.env["ykk.kpi.evaluation.rule"].search(
            [
                ("user_id", "=", employee_user.id),
                ("company_id", "=", self.company_id.id),
                ("active", "=", True),
            ],
            order="id desc",
            limit=1,
        )

    def _check_evaluation_rule(self):
        rule_id = self._get_evaluation_rule()
        if not rule_id:
            raise ValidationError(_("Please configure the Evaluation Rule."))

    def action_first_evaluate_activity(self):
        self._check_evaluation_rule()
        rule_id = self._get_evaluation_rule()
        model_id = self.env['ir.model']._get(self._name).id
        self.activity_schedule('ykk_kpi.mail_activity_first_evaluator_to_validate',
            summary='First To Validate',
            automated=True,
            res_id=self.id,
            res_model_id=model_id,
            user_id=rule_id.first_evaluator_id.id,
            date_deadline= fields.Date.today())

    def action_second_evaluate_activity(self):
        self._check_evaluation_rule()
        rule_id = self._get_evaluation_rule()
        model_id = self.env['ir.model']._get(self._name).id
        self.activity_schedule('ykk_kpi.mail_activity_second_evaluator_to_validate',
            summary='Second To Validate',
            automated=True,
            res_id=self.id,
            res_model_id=model_id,
            user_id=rule_id.second_evaluator_id.id,
            date_deadline= fields.Date.today())

    def _get_activity_feedback(self):
        return ['inprocess', 'evaluated']

    def _get_activity_unlink(self):
        return ['cancel']

    def activity_update(self):
        self.filtered(lambda x: x.state in self._get_activity_feedback()).activity_feedback(
            ['ykk_kpi.mail_activity_first_evaluator_to_validate', 'ykk_kpi.mail_activity_second_evaluator_to_validate'])
        self.filtered(lambda x: x.state in self._get_activity_unlink()).activity_unlink(
            ['ykk_kpi.mail_activity_first_evaluator_to_validate', 'ykk_kpi.mail_activity_second_evaluator_to_validate'])

    # -----------------------------------------------------
    # Calculate Grade
    # -----------------------------------------------------
    def _find_grade_by_score(self, score):
        self.ensure_one()
        return self.env["ykk.kpi.grade"].search(
            [
                ("company_id", "=", self.company_id.id),
                ("code", "=", str(score)),
            ],
            order="id desc",
            limit=1,
        )

    @api.depends(
        "performance_tab_total",
        "role_tab_total",
        "behavior_tab_total",
        "attitude_tab_total",
        "performance_line_ids",
        "role_line_ids",
        "behavior_line_ids",
        "attitude_line_ids",
        "company_id",
    )
    def _compute_period_grade(self):
        for record in self:
            tab_scores = []
            for line_field, total_field in [
                ("performance_line_ids", "performance_tab_total"),
                ("role_line_ids", "role_tab_total"),
                ("behavior_line_ids", "behavior_tab_total"),
                ("attitude_line_ids", "attitude_tab_total"),
            ]:
                if record[line_field]:
                    tab_scores.append(record[total_field])
            record.period_score = int(sum(tab_scores) / len(tab_scores)) if tab_scores else 0
            record.period_grade_id = record._find_grade_by_score(record.period_score) if tab_scores else False

    def _grade_code_to_score(self, grade):
        try:
            return int(grade.code)
        except (TypeError, ValueError):
            return False

    @api.depends(
        "period_grade_id",
        "summary_parent_kpi_ids.parent_kpi_id",
        "summary_parent_kpi_ids.parent_kpi_id.period_grade_id",
        "company_id",
    )
    def _compute_overall_grade(self):
        for record in self:
            grades = []
            if record.period_grade_id:
                grades.append(record.period_grade_id)
            grades.extend(
                line.parent_kpi_id.period_grade_id
                for line in record.summary_parent_kpi_ids
                if line.parent_kpi_id.period_grade_id
            )
            grade_scores = [
                score
                for score in (record._grade_code_to_score(grade) for grade in grades)
                if score is not False
            ]
            record.overall_score = int(sum(grade_scores) / len(grade_scores)) if grade_scores else 0
            record.overall_grade_id = (
                record._find_grade_by_score(record.overall_score)
                if grade_scores
                else False
            )

class KpiDepartmentKpiSummaryLine(models.Model):
    _name = "ykk.kpi.department.kpi.summary.line"
    _description = "Evaluation Summary Parent"

    department_kpi_id = fields.Many2one(
        "ykk.kpi.department.kpi",
        string="Evaluation",
        required=True,
        ondelete="cascade",
    )
    parent_kpi_id = fields.Many2one(
        "ykk.kpi.department.kpi",
        string="Parent KPI",
        required=True,
    )
    grade_id = fields.Many2one(
        "ykk.kpi.grade",
        string="Grade",
        related="parent_kpi_id.period_grade_id",
        readonly=True,
    )

    _sql_constraints = [
        (
            "department_parent_kpi_unique",
            "unique(department_kpi_id, parent_kpi_id)",
            "A Parent KPI can only be added once to the summary.",
        ),
    ]

class KpiDepartmentKpiPerformanceLine(models.Model):
    _name = "ykk.kpi.department.kpi.performance.line"
    _description = "KPI Evaluation Performance Line"

    department_kpi_id = fields.Many2one("ykk.kpi.department.kpi", string="Evaluation")
    evaluation_state = fields.Selection(related="department_kpi_id.state", string="Evaluation Status")
    goal_id = fields.Many2one("ykk.kpi.goal", string="Goal")
    achievement_criteria = fields.Text(string="Achievement Criteria")
    weight = fields.Float(string="Weight")
    comment_employee = fields.Text(string="Comment(Employee)")
    performance_result = fields.Text(string="Performance Results (Employee)")
    first_evaluator_comment = fields.Text(string="Comments (First Evaluator)")
    first_evaluator_score = fields.Float(string="Score (First Evaluator)", digits="KPI Score")
    comment_second_evaluator = fields.Text(string="Comment(Second Evaluator)")
    second_evaluator_score = fields.Float(string="Score (Second Evaluator)", digits="KPI Score")
    total_score = fields.Float(string="Total", digits="KPI Score", compute="_compute_total_score", store=True)

    group_kpi_user = fields.Boolean(related="department_kpi_id.group_kpi_user")
    can_edit_employee = fields.Boolean(related="department_kpi_id.can_edit_employee")
    can_edit_first_evaluator = fields.Boolean(related="department_kpi_id.can_edit_first_evaluator")
    can_edit_second_evaluator = fields.Boolean(related="department_kpi_id.can_edit_second_evaluator")

    @api.depends_context("uid")
    def _compute_group_kpi_user(self):
        user = self.env.user
        readonly_user = (
            user.has_group("ykk_kpi.group_ykk_kpi_user")
            and not user.has_group("ykk_kpi.group_ykk_kpi_admin")
        )
        for record in self:
            record.group_kpi_user = readonly_user

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
            "target": "new",
            "context": {
                **self.env.context,
                "create": False,
                "edit": False,
                "delete": False,
                "form_view_initial_mode": "readonly",
            },
        }

    @api.depends("second_evaluator_score", "weight")
    def _compute_total_score(self):
        for record in self:
            record.total_score = record.second_evaluator_score * (record.weight / 100.0)

    @api.constrains("first_evaluator_score", "second_evaluator_score")
    def _check_score_range(self):
        for record in self:
            for score in (record.first_evaluator_score, record.second_evaluator_score):
                if score and not (1.0 <= score <= 5.0):
                    raise ValidationError(_("Score (First/Second Evaluator) ต้องอยู่ระหว่าง 1 ถึง 5"))

class KpiDepartmentKpiRoleLine(models.Model):
    _name = "ykk.kpi.department.kpi.role.line"
    _description = "KPI Evaluation Role-based Behavior Evaluation Line"

    department_kpi_id = fields.Many2one("ykk.kpi.department.kpi", string="Evaluation")
    evaluation_state = fields.Selection(related="department_kpi_id.state", string="Evaluation Status")
    name = fields.Char(string="Goal")
    achievement_criteria = fields.Text(string="Achievement Criteria")
    weight = fields.Float(string="Weight")
    comment_employee = fields.Text(string="Comment(Employee)")
    performance_result = fields.Text(string="Performance Results (Employee)")
    first_evaluator_comment = fields.Text(string="Comments (First Evaluator)")
    first_evaluator_score = fields.Float(string="Score (First Evaluator)", digits="KPI Score")
    comment_second_evaluator = fields.Text(string="Comment(Second Evaluator)")
    second_evaluator_score = fields.Float(string="Score (Second Evaluator)", digits="KPI Score")
    total_score = fields.Float(string="Total", digits="KPI Score", compute="_compute_total_score", store=True)

    group_kpi_user = fields.Boolean(related="department_kpi_id.group_kpi_user")
    can_edit_employee = fields.Boolean(related="department_kpi_id.can_edit_employee")
    can_edit_first_evaluator = fields.Boolean(related="department_kpi_id.can_edit_first_evaluator")
    can_edit_second_evaluator = fields.Boolean(related="department_kpi_id.can_edit_second_evaluator")

    @api.depends("second_evaluator_score", "weight")
    def _compute_total_score(self):
        for record in self:
            record.total_score = record.second_evaluator_score * (record.weight / 100.0)

    @api.constrains("first_evaluator_score", "second_evaluator_score")
    def _check_score_range(self):
        for record in self:
            for score in (record.first_evaluator_score, record.second_evaluator_score):
                if score and not (1.0 <= score <= 5.0):
                    raise ValidationError(_("Score (First/Second Evaluator) ต้องอยู่ระหว่าง 1 ถึง 5"))

class KpiDepartmentKpiBehaviorLine(models.Model):
    _name = "ykk.kpi.department.kpi.behavior.line"
    _description = "KPI Evaluation Behavior Evaluation Line"

    department_kpi_id = fields.Many2one("ykk.kpi.department.kpi", string="Evaluation")
    evaluation_state = fields.Selection(related="department_kpi_id.state", string="Evaluation Status")
    name = fields.Char(string="Goal")
    achievement_criteria = fields.Text(string="Achievement Criteria")
    weight = fields.Float(string="Weight")
    comment_employee = fields.Text(string="Comment(Employee)")
    performance_result = fields.Text(string="Performance Results (Employee)")
    first_evaluator_comment = fields.Text(string="Comments (First Evaluator)")
    first_evaluator_score = fields.Float(string="Score (First Evaluator)", digits="KPI Score")
    comment_second_evaluator = fields.Text(string="Comment(Second Evaluator)")
    second_evaluator_score = fields.Float(string="Score (Second Evaluator)", digits="KPI Score")
    total_score = fields.Float(string="Total", digits="KPI Score", compute="_compute_total_score", store=True)

    group_kpi_user = fields.Boolean(related="department_kpi_id.group_kpi_user")
    can_edit_employee = fields.Boolean(related="department_kpi_id.can_edit_employee")
    can_edit_first_evaluator = fields.Boolean(related="department_kpi_id.can_edit_first_evaluator")
    can_edit_second_evaluator = fields.Boolean(related="department_kpi_id.can_edit_second_evaluator")

    @api.depends("second_evaluator_score", "weight")
    def _compute_total_score(self):
        for record in self:
            record.total_score = record.second_evaluator_score * (record.weight / 100.0)

    @api.constrains("first_evaluator_score", "second_evaluator_score")
    def _check_score_range(self):
        for record in self:
            for score in (record.first_evaluator_score, record.second_evaluator_score):
                if score and not (1.0 <= score <= 5.0):
                    raise ValidationError(_("Score (First/Second Evaluator) ต้องอยู่ระหว่าง 1 ถึง 5"))

class KpiDepartmentKpiAttitudeLine(models.Model):
    _name = "ykk.kpi.department.kpi.attitude.line"
    _description = "KPI Evaluation Attitude Evaluation Line"

    department_kpi_id = fields.Many2one("ykk.kpi.department.kpi", string="Evaluation")
    evaluation_state = fields.Selection(related="department_kpi_id.state", string="Evaluation Status")
    name = fields.Char(string="Goal")
    achievement_criteria = fields.Text(string="Achievement Criteria")
    weight = fields.Float(string="Weight")
    comment_employee = fields.Text(string="Comment(Employee)")
    performance_result = fields.Text(string="Performance Results (Employee)")
    first_evaluator_comment = fields.Text(string="Comments (First Evaluator)")
    first_evaluator_score = fields.Float(string="Score (First Evaluator)", digits="KPI Score")
    comment_second_evaluator = fields.Text(string="Comment(Second Evaluator)")
    second_evaluator_score = fields.Float(string="Score (Second Evaluator)", digits="KPI Score")
    total_score = fields.Float(string="Total", digits="KPI Score", compute="_compute_total_score", store=True)

    group_kpi_user = fields.Boolean(related="department_kpi_id.group_kpi_user")
    can_edit_employee = fields.Boolean(related="department_kpi_id.can_edit_employee")
    can_edit_first_evaluator = fields.Boolean(related="department_kpi_id.can_edit_first_evaluator")
    can_edit_second_evaluator = fields.Boolean(related="department_kpi_id.can_edit_second_evaluator")

    @api.depends("second_evaluator_score", "weight")
    def _compute_total_score(self):
        for record in self:
            record.total_score = record.second_evaluator_score * (record.weight / 100.0)

    @api.constrains("first_evaluator_score", "second_evaluator_score")
    def _check_score_range(self):
        for record in self:
            for score in (record.first_evaluator_score, record.second_evaluator_score):
                if score and not (1.0 <= score <= 5.0):
                    raise ValidationError(_("Score (First/Second Evaluator) ต้องอยู่ระหว่าง 1 ถึง 5"))
