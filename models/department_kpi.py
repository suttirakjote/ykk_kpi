from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

class KpiDepartmentKpi(models.Model):
    _name = "ykk.kpi.department.kpi"
    _description = "Department KPI"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = "id desc"

    name = fields.Char(string="Name", default='New', required=True, readonly=True)
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("inprocess", "Inprocess"),
            ("evaluated", "Evaluated"),
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
    annual_id = fields.Many2one("ykk.kpi.annual.kpi", string="Annual KPI")
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

    # Indicator Weight (read-only) ดึงจาก Annual KPI ที่อ้างอิง - แสดงใน tab Summary
    performance_weight = fields.Integer(related="annual_id.performance_weight", string="Performance Evaluation", readonly=True)
    role_based_behavior_weight = fields.Integer(related="annual_id.role_based_behavior_weight", string="Role-based Behavior Evaluation", readonly=True)
    behavior_weight = fields.Integer(related="annual_id.behavior_weight", string="Behavior Evaluation", readonly=True)
    attitude_weight = fields.Integer(related="annual_id.attitude_weight", string="Attitude Evaluation", readonly=True)

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
    
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('ykk.kpi.department.kpi') or 'New'
        return super(KpiDepartmentKpi, self).create(vals_list)

    def action_confirm(self):
        self.write({"state": "inprocess"})

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
        self.write({"state": "evaluated"})

    def action_cancel(self):
        self.write({"state": "cancel"})
    
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
    _description = "Department KPI Summary Parent"

    department_kpi_id = fields.Many2one(
        "ykk.kpi.department.kpi",
        string="Department KPI",
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
    _description = "KPI Department KPI Performance Line"

    department_kpi_id = fields.Many2one("ykk.kpi.department.kpi", string="Department KPI")
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
    _description = "KPI Department KPI Role-based Behavior Evaluation Line"

    department_kpi_id = fields.Many2one("ykk.kpi.department.kpi", string="Department KPI")
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
    _description = "KPI Department KPI Behavior Evaluation Line"

    department_kpi_id = fields.Many2one("ykk.kpi.department.kpi", string="Department KPI")
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
    _description = "KPI Department KPI Attitude Evaluation Line"

    department_kpi_id = fields.Many2one("ykk.kpi.department.kpi", string="Department KPI")
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
