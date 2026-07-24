from odoo import _, api, fields, models
from odoo.exceptions import UserError


class TemplateDocument(models.Model):
    _name = "ykk.kpi.template.document"
    _description = "Template Document"
    _order = "id desc"

    name = fields.Char(string="Reference", default="New", readonly=True, copy=False)
    employee_id = fields.Many2one("hr.employee", string="Employee")
    period_id = fields.Many2one("ykk.kpi.period", string="Period")
    date = fields.Date(string="Date", default=fields.Date.context_today)
    responsible_id = fields.Many2one(
        "res.users", string="Responsible", default=lambda self: self.env.user
    )
    company_id = fields.Many2one(
        "res.company", string="Company", required=True,
        default=lambda self: self.env.company,
    )
    salary_calculate_id = fields.Many2one(
        "ykk.kpi.salary.calculate", string="Salary Calculate"
    )
    bonus_calculate_id = fields.Many2one(
        "ykk.kpi.bonus.calculate", string="Bonus Calculate"
    )
    grade_id = fields.Many2one("ykk.kpi.grade", string="Grade")
    # --- จาก Salary Calculate ---
    current_salary = fields.Float(string="Current Salary")
    final_increase = fields.Float(string="Final Increase Salary")
    new_salary = fields.Float(string="New Salary")
    new_salary_month = fields.Float(string="New Salary Month")
    # --- จาก Bonus Calculate ---
    bonus = fields.Float(string="Bonus")
    bonus_grd = fields.Float(string="Bonus(GRD)")
    net_pay = fields.Float(string="Net Pay")

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", "New") == "New":
                vals["name"] = self.env["ir.sequence"].next_by_code(
                    "ykk.kpi.template.document") or "New"
        return super().create(vals_list)

    def action_load_data(self):
        """ดึงข้อมูลของพนักงานคนนี้จาก Salary Calculate + Bonus Calculate ที่เลือก"""
        self.ensure_one()
        if not self.employee_id:
            raise UserError(_("Please select an Employee first."))
        sl = self.salary_calculate_id.line_ids.filtered(
            lambda l: l.employee_id == self.employee_id)[:1]
        bl = self.bonus_calculate_id.line_ids.filtered(
            lambda l: l.employee_id == self.employee_id)[:1]
        vals = {
            "grade_id": False,
            "current_salary": 0.0, "final_increase": 0.0,
            "new_salary": 0.0, "new_salary_month": 0.0,
            "bonus": 0.0, "bonus_grd": 0.0, "net_pay": 0.0,
        }
        if sl:
            vals.update({
                "grade_id": sl.grade_id.id,
                "current_salary": sl.current_salary,
                "final_increase": sl.increase,
                "new_salary": sl.new_salary,
                "new_salary_month": sl.new_salary_month,
            })
        if bl:
            if not vals["grade_id"]:
                vals["grade_id"] = bl.grade_id.id
            vals.update({
                "bonus": bl.bonus,
                "bonus_grd": bl.bonus_grd,
                "net_pay": bl.net_pay,
            })
        self.write(vals)
        return True

    def action_print(self):
        return self.env.ref(
            "ykk_kpi_management.action_report_template_document"
        ).report_action(self)
