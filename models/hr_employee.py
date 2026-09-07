from datetime import datetime

from dateutil.relativedelta import relativedelta

from odoo import api, fields, models


class HrEmployee(models.Model):
    _inherit = "hr.employee"

    ykk_employee_code = fields.Char(string="Employee Code")
    # ชื่อภาษาไทย - ใช้ในเอกสารแจ้งการปรับค่าจ้าง (Template Document)
    ykk_thai_prefix = fields.Char(string="Thai Prefix")
    ykk_thai_first_name = fields.Char(string="Thai First Name")
    ykk_thai_last_name = fields.Char(string="Thai Last Name")
    ykk_thai_full_name = fields.Char(
        string="Thai Full Name", compute="_compute_ykk_thai_full_name"
    )
    ykk_kpi_salary = fields.Float(
        string="Salary",
        compute="_compute_ykk_kpi_salary",
        store=True,
    )
    ykk_kpi_level_id = fields.Many2one("ykk.kpi.level",string="Job Level")
    ykk_kpi_group_position_id = fields.Many2one("ykk.kpi.group.position", string="Group Position")
    ykk_kpi_employee_type = fields.Selection([
            ("monthly", "Monthly"),
            ("daily", "Daily")], string="Employee Type")
    ykk_start_work_date = fields.Date(string="Start Work Date")
    ykk_tenure = fields.Char(string="Tenure", compute="_compute_ykk_tenure")
    ykk_salary_month = fields.Float(string="Salary/Month", compute="_compute_ykk_salary_month", store=True)
    ykk_kpi_history_ids = fields.One2many("ykk.kpi.employee.history", "employee_id", string="KPI History")

    @api.depends("ykk_thai_prefix", "ykk_thai_first_name", "ykk_thai_last_name", "name")
    def _compute_ykk_thai_full_name(self):
        """คำนำหน้า + ชื่อ + สกุล (ภาษาไทย) - ถ้ายังไม่ได้กรอกให้ใช้ชื่อปกติแทน"""
        for employee in self:
            parts = [
                employee.ykk_thai_prefix,
                employee.ykk_thai_first_name,
                employee.ykk_thai_last_name,
            ]
            thai_name = " ".join(part.strip() for part in parts if part)
            employee.ykk_thai_full_name = thai_name or employee.name or ""

    @api.depends(
        "ykk_kpi_history_ids",
        "ykk_kpi_history_ids.year",
        "ykk_kpi_history_ids.salary",
        "ykk_kpi_history_ids.update",
    )
    def _compute_ykk_kpi_salary(self):
        for employee in self:
            if not employee.ykk_kpi_history_ids:
                employee.ykk_kpi_salary = 0.0
                continue
            latest_history = max(
                employee.ykk_kpi_history_ids,
                key=lambda history: (
                    history.year or 0,
                    history.update or datetime.min,
                    history._origin.id or 0,
                ),
            )
            employee.ykk_kpi_salary = latest_history.salary

    @api.depends("ykk_start_work_date")
    def _compute_ykk_tenure(self):
        today = fields.Date.context_today(self)
        for employee in self:
            if employee.ykk_start_work_date:
                if employee.ykk_start_work_date > today:
                    employee.ykk_tenure = "0 วัน 0 เดือน 0 ปี"
                    continue
                tenure = relativedelta(today, employee.ykk_start_work_date)
                employee.ykk_tenure = "%d วัน %d เดือน %d ปี" % (
                    tenure.days,
                    tenure.months,
                    tenure.years,
                )
            else:
                employee.ykk_tenure = ""

    @api.depends("ykk_kpi_salary", "ykk_kpi_employee_type")
    def _compute_ykk_salary_month(self):
        for employee in self:
            if employee.ykk_kpi_employee_type == "daily":
                employee.ykk_salary_month = employee.ykk_kpi_salary * 22
            else:
                employee.ykk_salary_month = employee.ykk_kpi_salary

    @api.depends("ykk_employee_code", "name")
    def _compute_display_name(self):
        super()._compute_display_name()
        for employee in self:
            if employee.ykk_employee_code and employee.display_name:
                employee.display_name = "[%s] %s" % (employee.ykk_employee_code, employee.display_name)
