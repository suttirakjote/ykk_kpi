from odoo import _, api, fields, models
from odoo.exceptions import AccessError, ValidationError, UserError
from odoo.tools.float_utils import float_round

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
            ("2_evaluated", "Evaluated"),
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
    annual_id = fields.Many2one(
        "ykk.kpi.annual.kpi",
        string="KPI/Goal Setting",
        copy=False,
        index=True,
        ondelete="restrict",
    )
    interview_line_ids = fields.One2many("ykk.kpi.department.kpi.interview.line", "department_kpi_id", string="Interview Performance")

    performance_line_ids = fields.One2many("ykk.kpi.department.kpi.performance.line", "department_kpi_id", string="Performance Evaluation")
    role_line_ids = fields.One2many("ykk.kpi.department.kpi.role.line", "department_kpi_id", string="Role-based Behavior Evaluation")
    behavior_line_ids = fields.One2many("ykk.kpi.department.kpi.behavior.line", "department_kpi_id", string="Behavior Evaluation")
    attitude_line_ids = fields.One2many("ykk.kpi.department.kpi.attitude.line", "department_kpi_id", string="Attitude Evaluation")
    total_score = fields.Float(string="Total", digits="KPI Score", compute="_compute_total_score", store=True)
    performance_tab_total = fields.Float(
        string="Performance Total",
        digits="KPI Score",
        compute="_compute_tab_totals",
        store=True,
    )
    role_tab_total = fields.Float(
        string="Role-based Behavior Total",
        digits="KPI Score",
        compute="_compute_tab_totals",
        store=True,
    )
    behavior_tab_total = fields.Float(
        string="Behavior Total",
        digits="KPI Score",
        compute="_compute_tab_totals",
        store=True,
    )
    attitude_tab_total = fields.Float(
        string="Attitude Total",
        digits="KPI Score",
        compute="_compute_tab_totals",
        store=True,
    )
    period_score = fields.Float(
        string="Period Score",
        digits="KPI Score",
        compute="_compute_period_grade",
    )
    period_grade_id = fields.Many2one("ykk.kpi.grade", string="Period Grade", compute="_compute_period_grade")
    summary_parent_kpi_ids = fields.One2many(
        "ykk.kpi.department.kpi.summary.line",
        "department_kpi_id",
        string="Parent KPIs",
    )
    overall_score = fields.Float(
        string="Overall Score",
        digits="KPI Score",
        compute="_compute_overall_grade",
    )
    adjust_grade = fields.Char(
        string="Adjust Grade",
        compute="_compute_adjust_grade",
    )
    adjust_score = fields.Float(
        string="Adjust Score",
        digits="KPI Score",
        compute="_compute_adjust_score",
    )
    overall_grade_id = fields.Many2one("ykk.kpi.grade", string="Overall Grade", compute="_compute_overall_grade")
    company_id = fields.Many2one("res.company", string="Company", required=True, default=lambda self: self.env.company)
    group_kpi_user = fields.Boolean(compute="_compute_group_kpi_user")
    can_edit_employee = fields.Boolean(compute="_compute_evaluation_permissions")
    can_edit_first_evaluator = fields.Boolean(compute="_compute_evaluation_permissions")
    can_edit_second_evaluator = fields.Boolean(compute="_compute_evaluation_permissions")
    current_employee = fields.Boolean(compute="_compute_current_employee")

    # Indicator Weight (read-only) ดึงจาก KPI/Goal Setting ที่อ้างอิง - แสดงใน tab Summary
    performance_weight = fields.Integer(related="annual_id.performance_weight", string="Performance Evaluation", readonly=True)
    role_based_behavior_weight = fields.Integer(related="annual_id.role_based_behavior_weight", string="Role-based Behavior Evaluation", readonly=True)
    behavior_weight = fields.Integer(related="annual_id.behavior_weight", string="Behavior Evaluation", readonly=True)
    attitude_weight = fields.Integer(related="annual_id.attitude_weight", string="Attitude Evaluation", readonly=True)

    description = fields.Html(string='Description', sanitize_attributes=False)
    evaluation_topic = fields.Selection(related="level_id.evaluation_topic", string="Evaluation Topic")

    attitude_tab_remaining = fields.Float(
        string="Remaining Score",
        digits="KPI Score",
        compute="_compute_tab_totals",
        store=True,
    )
    attitude_tab_evaluation = fields.Float(
        string="Evaluation Score",
        digits="KPI Score",
        compute="_compute_tab_totals",
        store=True,
    )

    @api.depends_context("uid")
    def _compute_group_kpi_user(self):
        user = self.env.user
        readonly_user = (
            user.has_group("ykk_kpi.group_ykk_kpi_user")
            and not user.has_group("ykk_kpi.group_ykk_kpi_admin")
        )
        for record in self:
            record.group_kpi_user = readonly_user

    @api.depends("employee_id.user_id", "department_id", "company_id")
    @api.depends_context("uid")
    def _compute_evaluation_permissions(self):
        current_user = self.env.user
        for record in self:
            rule = record._get_evaluation_rule()
            is_current_employee = record.employee_id.user_id == current_user
            is_employee_rule = (rule and rule.rule_type == "employee" and rule.user_id == current_user)
            is_department_rule = (rule and rule.rule_type == "department" and rule.department_id == record.employee_id.department_id)
            record.can_edit_employee = bool(rule and is_current_employee and (is_employee_rule or is_department_rule))
            # Evaluator
            record.can_edit_first_evaluator = bool(rule and rule.first_evaluator_id == current_user)
            record.can_edit_second_evaluator = bool(rule and rule.second_evaluator_id == current_user)

    @api.depends("employee_id.user_id")
    @api.depends_context("uid")
    def _compute_current_employee(self):
        current_user = self.env.user
        for record in self:
            record.current_employee = (
                record.employee_id.user_id == current_user
            )

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
        "attitude_line_ids.total_score")
    def _compute_tab_totals(self):
        for record in self:
            record.performance_tab_total = sum(record.performance_line_ids.mapped("total_score"))
            role_scores = record.role_line_ids.mapped("total_score")
            behavior_scores = record.behavior_line_ids.mapped("total_score")
            record.role_tab_total = (sum(role_scores) / len(role_scores) if role_scores else 0.0)
            record.behavior_tab_total = (sum(behavior_scores) / len(behavior_scores) if behavior_scores else 0.0)
            # Tab Attitude
            attitude_tab_total = sum(record.attitude_line_ids.mapped("total_score"))
            attitude_tab_remaining = 50 + attitude_tab_total
            attitude_tab_evaluation = attitude_tab_remaining / 10
            record.attitude_tab_total = attitude_tab_total
            record.attitude_tab_remaining = attitude_tab_remaining
            record.attitude_tab_evaluation = 0.0 if attitude_tab_evaluation < 0.0 else attitude_tab_evaluation

    @api.depends("employee_id")
    def _compute_employee_info(self):
        for record in self:
            record.group_position_id = record.employee_id.ykk_kpi_group_position_id
            record.level_id = record.employee_id.ykk_kpi_level_id
            record.department_id = record.employee_id.department_id

    @api.onchange("employee_id")
    def _onchange_employee_id(self):
        for record in self:
            annual = self.env["ykk.kpi.annual.kpi"]
            attitude_line_commands = [(5, 0, 0)]
            if record.employee_id:
                annual = annual.search([
                    ("employee_id", "=", record.employee_id.id),
                    ("state", "=", "done")], order="id desc", limit=1)
                evaluations = self.env["ykk.kpi.hr.evaluation"].search([
                    ("type", "=", "attitude"),
                    ("company_id", "=", record.company_id.id),
                    ("active", "=", True),
                ])
                attitude_line_commands.extend([
                    (0, 0, {
                        "name": evaluation.name,
                        "hr_evaluation_code": evaluation.code,
                        "deduction_score": -abs(evaluation.deduction_score or 0),
                    })
                    for evaluation in evaluations
                ])
            record.annual_id = annual
            record.period_id = annual.period_id if annual else False
            record.attitude_line_ids = attitude_line_commands

    def action_send_approve(self):
        self.ensure_one()
        self._check_evaluation_rule()
        rule_id = self._get_evaluation_rule()
        if not rule_id.first_evaluator_id:
            raise ValidationError(
                _("Please configure the First Evaluator in the Evaluation Rule.")
            )
        is_kpi_admin = self.env.user.has_group("ykk_kpi.group_ykk_kpi_admin")
        if self.employee_id.user_id != self.env.user and not is_kpi_admin:
            raise UserError(
                _("Only the employee or KPI Administrator can send for approval.")
            )

        activity_type = self.env.ref(
            "ykk_kpi.mail_activity_first_evaluator_to_validate"
        )
        existing_activity = self.activity_ids.filtered(
            lambda activity: activity.activity_type_id == activity_type
            and activity.user_id == rule_id.first_evaluator_id
        )
        if existing_activity:
            message = _("An approval activity has already been sent.")
            notification_type = "warning"
        else:
            self.action_first_evaluate_activity()
            message = _("The approval activity was sent successfully.")
            notification_type = "success"

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Send Approve"),
                "message": message,
                "type": notification_type,
                "sticky": False,
                "next": {
                    "type": "ir.actions.client",
                    "tag": "soft_reload",
                },
            },
        }

    # 1st Evaluate
    def action_confirm(self):
        self._check_evaluation_rule()
        rule_id = self._get_evaluation_rule()
        if rule_id.first_evaluator_id != self.env.user:
            raise UserError(_("You do not have permission as the First Evaluator."))
        if not rule_id.second_evaluator_id:
            raise ValidationError(_("Please configure the Second Evaluator in the Evaluation Rule."))
        self.write({"state": "inprocess"})
        self.activity_update()
        self.action_second_evaluate_activity()

    # 2nd Evaluate
    def action_done(self):
        for record in self:
            errors = []
            tabs = [(_("Performance Evaluation"), record.performance_line_ids)]
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

    # Evaluated
    def action_approve(self):
        records_to_approve = self.filtered(lambda record: record.state == "evaluated")
        updated_count = len(records_to_approve)
        skipped_count = len(self) - updated_count
        if records_to_approve:
            records_to_approve.write({"state": "2_evaluated"})
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

    # Approve
    def action_evaluated(self):
        self.write({"state": "approved"})

    def action_cancel(self):
        self.write({"state": "cancel"})
        self.activity_update()

    def action_draft(self):
        self.write({"state": "draft"})

    def _get_evaluation_rule(self):
        self.ensure_one()
        rule_model = self.env["ykk.kpi.evaluation.rule"]
        domain = [
            ("company_id", "=", self.company_id.id),
            ("active", "=", True),
        ]
        employee_user = self.employee_id.user_id
        employee_department = self.employee_id.department_id
        domain += [
            "|",
            "&",
            ("rule_type", "=", "employee"),
            ("user_id", "=", employee_user.id),
            "&",
            ("rule_type", "=", "department"),
            ("department_id", "=", employee_department.id),
        ]
        return rule_model.search(domain, order="id desc", limit=1)

    def _check_evaluation_rule(self):
        rule_id = self._get_evaluation_rule()
        if not rule_id:
            raise ValidationError(_("Please configure the Evaluation Rule."))

    def action_first_evaluate_activity(self):
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
        # Grade codes are configured as whole-number values. Keep the existing
        # grade selection behavior while allowing the displayed score to retain
        # its decimal portion.
        grade_code = str(int(score))
        return self.env["ykk.kpi.grade"].search(
            [
                ("company_id", "=", self.company_id.id),
                ("code", "=", grade_code),
            ],
            order="id desc",
            limit=1,
        )

    @api.depends(
        "performance_tab_total",
        "role_tab_total",
        "behavior_tab_total",
        "attitude_tab_evaluation",
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
                ("attitude_line_ids", "attitude_tab_evaluation"),
            ]:
                if record[line_field]:
                    tab_scores.append(record[total_field])
            record.period_score = (
                float_round(sum(tab_scores) / len(tab_scores), precision_digits=2)
                if tab_scores
                else 0.0
            )
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
            record.overall_score = (
                float_round(sum(grade_scores) / len(grade_scores), precision_digits=2)
                if grade_scores
                else 0.0
            )
            record.overall_grade_id = (
                record._find_grade_by_score(record.overall_score)
                if grade_scores
                else False
            )

    def _compute_adjust_grade(self):
        adjustment_line_model = self.env["kpi.adjustment.line"]
        for record in self:
            grade = False
            if record.id:
                line = adjustment_line_model.search(
                    [("department_kpi_id", "=", record.id)],
                    order="id desc",
                    limit=1,
                )
                if line:
                    grade = line.new_grade if line.is_changed else line.current_grade
            record.adjust_grade = grade

    @api.depends("adjust_grade", "company_id")
    def _compute_adjust_score(self):
        for record in self:
            grade = record._get_adjust_grade_record()
            record.adjust_score = grade.end_score if grade else 0.0

    def _get_adjust_grade_record(self):
        """Convert the adjusted grade name to its grade configuration record."""
        self.ensure_one()
        if not self.adjust_grade:
            return self.env["ykk.kpi.grade"]
        return self.env["ykk.kpi.grade"].search(
            [
                ("name", "=", self.adjust_grade),
                ("company_id", "=", self.company_id.id),
            ],
            limit=1,
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

class KpiDepartmentKpiInterviewLine(models.Model):
    _name = "ykk.kpi.department.kpi.interview.line"
    _description = "KPI Evaluation Interview Line"

    department_kpi_id = fields.Many2one("ykk.kpi.department.kpi", string="Evaluation")
    evaluation_state = fields.Selection(related="department_kpi_id.state", string="Evaluation Status")
    goal_id = fields.Many2one("ykk.kpi.goal", string="Goal")
    achievement_criteria = fields.Text(string="Achievement Criteria")
    weight = fields.Float(string="Weight")
    comment_employee = fields.Text(string="Comment(Employee)")
    performance_result = fields.Float(string="Performance Results (Employee)")
    first_evaluator_comment = fields.Text(string="Comments (First Evaluator)")
    first_evaluator_score = fields.Float(string="Score (First Evaluator)", digits="KPI Score")
    comment_second_evaluator = fields.Text(string="Comment(Second Evaluator)")
    second_evaluator_score = fields.Float(string="Score (Second Evaluator)", digits="KPI Score")
    total_score = fields.Float(string="Total", digits="KPI Score", compute="_compute_total_score", store=True)

    @api.depends("second_evaluator_score", "weight")
    def _compute_total_score(self):
        for record in self:
            record.total_score = record.second_evaluator_score * (record.weight / 100.0)

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

class KpiDepartmentKpiPerformanceLine(models.Model):
    _name = "ykk.kpi.department.kpi.performance.line"
    _description = "KPI Evaluation Performance Line"

    department_kpi_id = fields.Many2one("ykk.kpi.department.kpi", string="Evaluation")
    evaluation_state = fields.Selection(related="department_kpi_id.state", string="Evaluation Status")
    goal_id = fields.Many2one("ykk.kpi.goal", string="Goal")
    achievement_criteria = fields.Text(string="Achievement Criteria")
    weight = fields.Float(string="Weight")
    comment_employee = fields.Text(string="Comment(Employee)")
    performance_result = fields.Float(string="Performance Results (Employee)")
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

    @api.constrains(
        "performance_result",
        "first_evaluator_score",
        "second_evaluator_score",
    )
    def _check_score_range(self):
        for record in self:
            if not 0.0 <= record.performance_result <= 5.0:
                raise ValidationError(_("Performance Results (Employee) ต้องอยู่ระหว่าง 0 ถึง 5"))
            if not 0.0 <= record.first_evaluator_score <= 5.0:
                raise ValidationError(_("Score (First Evaluator) ต้องอยู่ระหว่าง 0 ถึง 5"))
            elif not 0.0 <= record.second_evaluator_score <= 5.0:
                raise ValidationError(_("Score (Second Evaluator) ต้องอยู่ระหว่าง 0 ถึง 5"))

class KpiDepartmentKpiRoleLine(models.Model):
    _name = "ykk.kpi.department.kpi.role.line"
    _description = "KPI Evaluation Role-based Behavior Evaluation Line"

    department_kpi_id = fields.Many2one("ykk.kpi.department.kpi", string="Evaluation")
    evaluation_state = fields.Selection(related="department_kpi_id.state", string="Evaluation Status")
    name = fields.Char(string="Goal")
    achievement_criteria = fields.Text(string="Achievement Criteria")
    weight = fields.Float(string="Weight")
    comment_employee = fields.Text(string="Comment(Employee)")
    performance_result = fields.Float(string="Performance Results (Employee)")
    first_evaluator_comment = fields.Text(string="Comments (First Evaluator)")
    first_evaluator_score = fields.Float(string="Score (First Evaluator)", digits="KPI Score")
    comment_second_evaluator = fields.Text(string="Comment(Second Evaluator)")
    second_evaluator_score = fields.Float(string="Score (Second Evaluator)", digits="KPI Score")
    total_score = fields.Float(string="Total", digits="KPI Score", compute="_compute_total_score", store=True)

    group_kpi_user = fields.Boolean(related="department_kpi_id.group_kpi_user")
    can_edit_employee = fields.Boolean(related="department_kpi_id.can_edit_employee")
    can_edit_first_evaluator = fields.Boolean(related="department_kpi_id.can_edit_first_evaluator")
    can_edit_second_evaluator = fields.Boolean(related="department_kpi_id.can_edit_second_evaluator")

    @api.depends("second_evaluator_score")
    def _compute_total_score(self):
        for record in self:
            record.total_score = record.second_evaluator_score

    @api.constrains(
        "performance_result",
        "first_evaluator_score",
        "second_evaluator_score",
    )
    def _check_score_range(self):
        for record in self:
            if not 0.0 <= record.performance_result <= 5.0:
                raise ValidationError(_("Performance Results (Employee) ต้องอยู่ระหว่าง 0 ถึง 5"))
            if not 0.0 <= record.first_evaluator_score <= 5.0:
                raise ValidationError(_("Score (First Evaluator) ต้องอยู่ระหว่าง 0 ถึง 5"))
            elif not 0.0 <= record.second_evaluator_score <= 5.0:
                raise ValidationError(_("Score (Second Evaluator) ต้องอยู่ระหว่าง 0 ถึง 5"))

class KpiDepartmentKpiBehaviorLine(models.Model):
    _name = "ykk.kpi.department.kpi.behavior.line"
    _description = "KPI Evaluation Behavior Evaluation Line"

    department_kpi_id = fields.Many2one("ykk.kpi.department.kpi", string="Evaluation")
    evaluation_state = fields.Selection(related="department_kpi_id.state", string="Evaluation Status")
    name = fields.Char(string="Goal")
    achievement_criteria = fields.Text(string="Achievement Criteria")
    weight = fields.Float(string="Weight")
    comment_employee = fields.Text(string="Comment(Employee)")
    performance_result = fields.Float(string="Performance Results (Employee)")
    first_evaluator_comment = fields.Text(string="Comments (First Evaluator)")
    first_evaluator_score = fields.Float(string="Score (First Evaluator)", digits="KPI Score")
    comment_second_evaluator = fields.Text(string="Comment(Second Evaluator)")
    second_evaluator_score = fields.Float(string="Score (Second Evaluator)", digits="KPI Score")
    total_score = fields.Float(string="Total", digits="KPI Score", compute="_compute_total_score", store=True)

    group_kpi_user = fields.Boolean(related="department_kpi_id.group_kpi_user")
    can_edit_employee = fields.Boolean(related="department_kpi_id.can_edit_employee")
    can_edit_first_evaluator = fields.Boolean(related="department_kpi_id.can_edit_first_evaluator")
    can_edit_second_evaluator = fields.Boolean(related="department_kpi_id.can_edit_second_evaluator")

    @api.depends("second_evaluator_score")
    def _compute_total_score(self):
        for record in self:
            record.total_score = record.second_evaluator_score

    @api.constrains(
        "performance_result",
        "first_evaluator_score",
        "second_evaluator_score",
    )
    def _check_score_range(self):
        for record in self:
            if not 0.0 <= record.performance_result <= 5.0:
                raise ValidationError(_("Performance Results (Employee) ต้องอยู่ระหว่าง 0 ถึง 5"))
            if not 0.0 <= record.first_evaluator_score <= 5.0:
                raise ValidationError(_("Score (First Evaluator) ต้องอยู่ระหว่าง 0 ถึง 5"))
            elif not 0.0 <= record.second_evaluator_score <= 5.0:
                raise ValidationError(_("Score (Second Evaluator) ต้องอยู่ระหว่าง 0 ถึง 5"))

class KpiDepartmentKpiAttitudeLine(models.Model):
    _name = "ykk.kpi.department.kpi.attitude.line"
    _description = "KPI Evaluation Attitude Evaluation Line"

    department_kpi_id = fields.Many2one("ykk.kpi.department.kpi", string="Evaluation")
    evaluation_state = fields.Selection(related="department_kpi_id.state", string="Evaluation Status")
    name = fields.Char(string="Goal")
    hr_evaluation_code = fields.Char(string="HR Evaluation Code", index=True)
    deduction_score = fields.Integer(string="Deduction Score")
    frequency = fields.Integer(string="Frequency")
    total_score = fields.Float(string="Total", digits="KPI Score", compute="_compute_total_score", store=True)

    group_kpi_user = fields.Boolean(related="department_kpi_id.group_kpi_user")
    can_edit_employee = fields.Boolean(related="department_kpi_id.can_edit_employee")
    can_edit_first_evaluator = fields.Boolean(related="department_kpi_id.can_edit_first_evaluator")
    can_edit_second_evaluator = fields.Boolean(related="department_kpi_id.can_edit_second_evaluator")

    @api.depends("deduction_score", "frequency")
    def _compute_total_score(self):
        for record in self:
            record.total_score = record.deduction_score * record.frequency
