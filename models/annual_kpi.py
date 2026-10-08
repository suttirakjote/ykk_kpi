from odoo import _, api, fields, models
from odoo.exceptions import ValidationError, UserError
from odoo.tools import float_compare


class KpiAnnualKpi(models.Model):
    _name = "ykk.kpi.annual.kpi"
    _description = "KPI/Goal Setting"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = "id desc"

    @api.model
    def _default_period_id(self):
        today = fields.Date.context_today(self)
        return self.env["ykk.kpi.period"].search(
            [
                ("start_date", "<=", today),
                ("end_date", ">=", today),
                ("company_id", "=", self.env.company.id),
            ],
            order="id desc",
            limit=1,
        )

    @api.model
    def _find_kpi_template(self, employee, period):
        if not employee or not period:
            return self.env["ykk.kpi.template"]
        return self.env["ykk.kpi.template"].search([
            ("employee_ids", "in", employee.id),
            ("department_id", "=", employee.department_id.id),
            ("level_id", "=", employee.ykk_kpi_level_id.id),
            ("period_id", "=", period.id),
            ("state", "=", "done")], order="id desc", limit=1)

    @api.model
    def _default_template_id(self):
        return self._find_kpi_template(self.env.user.employee_id, self._default_period_id())

    name = fields.Char(string="Name", default='New', required=True, readonly=True)
    state = fields.Selection([
        ("draft", "Self Evaluate"),
        ("1_approve", "1st Approved"),
        ("2_approve", "2nd Approved"),
        ("waiting_approve", "Waiting Approve"),
        ("reject", "Rejected"),
        ("revise", "Revised"),
        ("done", "Done"),
        ("cancel", "Cancel")], string="Status", default="draft", required=True, tracking=True)

    employee_id = fields.Many2one(
        "hr.employee",
        string="Employee",
        required=True,
        tracking=True,
        default=lambda self: self.env.user.employee_id,
    )
    employee_code = fields.Char(string="Employee Code", related="employee_id.ykk_employee_code")
    group_position_id = fields.Many2one("ykk.kpi.group.position", string="Group Position", compute="_compute_employee_info", store=True, readonly=True, tracking=True)
    level_id = fields.Many2one("ykk.kpi.level", string="Job Level", compute="_compute_employee_info", store=True, readonly=True, tracking=True)
    evaluation_topic = fields.Selection(related="level_id.evaluation_topic", string="Evaluation Topic")

    department_id = fields.Many2one("hr.department", string="Department", compute="_compute_employee_info", store=True, readonly=True, tracking=True)
    period_id = fields.Many2one(
        "ykk.kpi.period",
        string="Period",
        required=True,
        tracking=True,
        default=_default_period_id,
    )
    responsible_id = fields.Many2one("res.users", string="Responsible", default=lambda self: self.env.user)
    date = fields.Date(string='Date', default=fields.Date.context_today)
    company_id = fields.Many2one("res.company", string="Company", required=True, default=lambda self: self.env.company)
    evaluation_id = fields.Many2one(
        "ykk.kpi.department.kpi",
        string="Evaluation",
        compute="_compute_evaluation_id",
    )
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
    can_edit_employee = fields.Boolean(compute="_compute_evaluation_permissions")
    can_edit_first_evaluator = fields.Boolean(compute="_compute_evaluation_permissions")
    can_edit_second_evaluator = fields.Boolean(compute="_compute_evaluation_permissions")
    current_employee = fields.Boolean(compute="_compute_current_employee")

    template_id = fields.Many2one("ykk.kpi.template", string="KPI Template", default=_default_template_id)

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

    def _compute_evaluation_id(self):
        evaluations_by_annual = {}
        if self.ids:
            evaluations = self.env["ykk.kpi.department.kpi"].search(
                [("annual_id", "in", self.ids)],
                order="id desc",
            )
            for evaluation in evaluations:
                evaluations_by_annual.setdefault(
                    evaluation.annual_id.id,
                    evaluation,
                )
        for record in self:
            record.evaluation_id = evaluations_by_annual.get(record.id, False)

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

    @api.onchange("level_id")
    def _onchange_level_id(self):
        for record in self:
            level = record.level_id
            record.performance_weight = level.performance_weight if level else 0
            record.role_based_behavior_weight = (
                level.role_based_behavior_weight if level else 0
            )
            record.behavior_weight = level.behavior_weight if level else 0
            record.attitude_weight = level.attitude_weight if level else 0

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if "indicator_weight" not in vals and vals.get("employee_id"):
                employee = self.env["hr.employee"].browse(vals["employee_id"])
                vals["indicator_weight"] = (
                    employee.ykk_kpi_level_id.indicator_weight
                )
        return super().create(vals_list)

    def write(self, vals):
        result = super().write(vals)
        positive_attitude_lines = self.mapped("attitude_line_ids").filtered(
            lambda line: line.deduction_score > 0
        )
        for line in positive_attitude_lines:
            line.write({"deduction_score": -line.deduction_score})
        return result

    @api.onchange("employee_id", "period_id")
    def _onchange_employee_id(self):
        for record in self:
            if record.employee_id:
                record.indicator_weight = (
                    record.employee_id.ykk_kpi_level_id.indicator_weight
                )
                record._onchange_level_id()
                template = record._find_kpi_template(
                    record.employee_id,
                    record.period_id,
                )
                record.template_id = template
                record._set_performance_lines_from_template(template)
                record._set_role_lines_from_hr_evaluation()
                record._set_behavior_lines_from_hr_evaluation()
                record._set_attitude_lines_from_hr_evaluation()
            else:
                record.indicator_weight = 0
                record._onchange_level_id()
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
                evaluations = self.env["ykk.kpi.hr.evaluation"].search([
                    ("type", "=", "role_based_behavior"),
                    ("level_ids", "in", [record.employee_id.ykk_kpi_level_id.id])])
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
                evaluations = self.env["ykk.kpi.hr.evaluation"].search([
                    ("type", "=", "behavior"),
                    ("level_ids", "in", [record.employee_id.ykk_kpi_level_id.id])])
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
                evaluations = self.env["ykk.kpi.hr.evaluation"].search([
                    ("type", "=", "attitude"),
                    ("company_id", "=", record.company_id.id),
                    ("active", "=", True)])
                attitude_line_commands.extend([
                    (0, 0, {
                        "name": evaluation.display_name,
                        "hr_evaluation_code": evaluation.code,
                        # "achievement_criteria": evaluation.achievement_criteria,
                        # "criteria_details": evaluation.criteria_details,
                        "deduction_score": -abs(evaluation.deduction_score or 0),
                    })
                    for evaluation in evaluations
                ])
            record.attitude_line_ids = attitude_line_commands

    def action_send_approve(self):
        self.ensure_one()
        self._check_evaluation_rule()
        rule_id = self._get_evaluation_rule()

        is_kpi_admin = self.env.user.has_group("ykk_kpi.group_ykk_kpi_admin")
        if self.employee_id.user_id != self.env.user and not is_kpi_admin:
            raise UserError(_("Only the employee or KPI Administrator can send for approval."))

        activity_type = self.env.ref("ykk_kpi.mail_activity_first_evaluator_to_validate")
        existing_activity = self.activity_ids.filtered(lambda activity: activity.activity_type_id == activity_type
            and activity.user_id == rule_id.first_evaluator_id)
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

    def action_1_approve(self):
        self._check_evaluation_rule()
        rule_id = self._get_evaluation_rule()
        if rule_id.first_evaluator_id != self.env.user:
            raise UserError(_("You do not have permission as the First Evaluator."))
        if not rule_id.second_evaluator_id:
            raise ValidationError(
                _("Please configure the Second Evaluator in the Evaluation Rule.")
            )
        self.write({"state": "1_approve"})
        self.activity_update()
        self.action_second_evaluate_activity()

    def action_2_approve(self):
        self._check_evaluation_rule()
        rule_id = self._get_evaluation_rule()
        if rule_id.second_evaluator_id != self.env.user:
            raise UserError(_("You do not have permission as the Second Evaluator."))
        self.write({"state": "2_approve"})
        self.activity_update()

    def action_confirm(self):
        self._check_weight_total()
        # Update State and Activity
        self.activity_update()
        self.write({"state": "waiting_approve"})

    def action_reject(self):
        self.write({"state": "reject"})

    def action_revise(self):
        self.write({"state": "revise"})

    def _check_weight_total(self):
        invalid_documents = []
        for record in self:
            invalid_weight = record.weight_total != 100
            tabs = [record.performance_line_ids]
            for lines in tabs:
                if lines and abs(sum(lines.mapped("weight")) - 100.0) > 0.01:
                    invalid_weight = True
                    break
            if invalid_weight:
                invalid_documents.append(record.display_name)

        if invalid_documents:
            raise ValidationError(
                _("Weight must be 100%% for the following documents:\n- %s")
                % "\n- ".join(invalid_documents)
            )

    def action_approve(self):
        state_records = self.filtered(
            lambda record: record.state in ["waiting_approve", "revise"]
        )
        invalid_state_count = len(self) - len(state_records)
        state_records._check_weight_total()
        records_to_approve = state_records
        updated_count = len(records_to_approve)
        skipped_count = invalid_state_count
        if records_to_approve:
            records_to_approve.write({"state": "done"})

        message = _(
            "Updated successfully: %(updated)s record(s).\n"
            "Skipped: %(skipped)s record(s).",
            updated=updated_count,
            skipped=skipped_count,
        )

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Select Approve Summary"),
                "message": message,
                "type": "success" if not skipped_count else "warning",
                "sticky": False,
                "next": {
                    "type": "ir.actions.client",
                    "tag": "soft_reload",
                },
            },
        }

    def action_create_evaluation(self):
        created_count = 0
        skipped_count = 0
        evaluation_model = self.env["ykk.kpi.department.kpi"]

        for record in self:
            # if record.state != "done" or record.evaluation_id:
            #     skipped_count += 1
            #     continue

            evaluation_model.create({
                "employee_id": record.employee_id.id,
                "period_id": record.period_id.id,
                "annual_id": record.id,
                "responsible_id": record.responsible_id.id,
                "date": record.date,
                "company_id": record.company_id.id,
                "attitude_line_ids": [
                    (0, 0, {
                        "name": line.name,
                        "hr_evaluation_code": line.hr_evaluation_code,
                        "deduction_score": line.deduction_score,
                    })
                    for line in record.attitude_line_ids
                ],
            })
            created_count += 1

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Create Evaluation Summary"),
                "message": _(
                    "Created successfully: %(created)s record(s).\n"
                    "Skipped: %(skipped)s record(s).",
                    created=created_count,
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

    def action_draft(self):
        self.write({"state": "draft"})


    # def _get_evaluation_rule(self):
    #     self.ensure_one()
    #     employee_user = self.employee_id.user_id
    #     if not employee_user:
    #         return self.env["ykk.kpi.evaluation.rule"]

    #     return self.env["ykk.kpi.evaluation.rule"].search([
    #         ("user_id", "=", employee_user.id),
    #         ("company_id", "=", self.company_id.id),
    #         ("active", "=", True)], order="id desc", limit=1)

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
        return ['1_approve', '2_approve']

    def _get_activity_unlink(self):
        return ['cancel']

    def activity_update(self):
        self.filtered(lambda x: x.state in self._get_activity_feedback()).activity_feedback(
            ['ykk_kpi.mail_activity_first_evaluator_to_validate', 'ykk_kpi.mail_activity_second_evaluator_to_validate'])
        self.filtered(lambda x: x.state in self._get_activity_unlink()).activity_unlink(
            ['ykk_kpi.mail_activity_first_evaluator_to_validate', 'ykk_kpi.mail_activity_second_evaluator_to_validate'])

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
    hr_evaluation_code = fields.Char(string="HR Evaluation Code", index=True)
    achievement_criteria = fields.Text(string="Achievement Criteria")
    criteria_details = fields.Text(string="Criteria Details")
    weight = fields.Float(string="Weight")
    deduction_score = fields.Integer(string="Deduction Score")

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if "deduction_score" in vals:
                vals["deduction_score"] = -abs(vals["deduction_score"] or 0)
        return super().create(vals_list)

    def write(self, vals):
        if "deduction_score" in vals:
            vals = dict(vals)
            vals["deduction_score"] = -abs(vals["deduction_score"] or 0)
        return super().write(vals)
