# -*- coding: utf-8 -*-
from odoo import models, fields, _
from odoo.exceptions import UserError


class SalaryCalculate(models.Model):
    _inherit = "ykk.kpi.salary.calculate"

    def action_load_employee(self):
        """โหลดพนักงานจาก Evaluation (period ตรง + approved)
        และเซ็ต Grade ของบรรทัด = Adjust Grade ของเอกสารนั้น"""
        self.ensure_one()
        if not self.period_id:
            raise UserError(_("Please select a Period first."))
        department_kpis = self.env['ykk.kpi.department.kpi'].search([
            ('period_id', '=', self.period_id.id),
            ('state', '=', 'approved'),
        ])
        History = self.env['ykk.kpi.employee.history']
        current_year = fields.Date.context_today(self).year
        seen = set(self.line_ids.mapped('employee_id').ids)
        lines = []
        for kpi in department_kpis:
            if not kpi.employee_id or kpi.employee_id.id in seen:
                continue
            seen.add(kpi.employee_id.id)
            grade = kpi._get_adjust_grade_record()
            # Over Leave Day = KPI History ของพนักงานปีปัจจุบัน (จาก Import HR Data)
            history = History.search([
                ('employee_id', '=', kpi.employee_id.id),
                ('year', '=', current_year),
            ], limit=1)
            lines.append((0, 0, {
                'employee_id': kpi.employee_id.id,
                'grade_id': grade.id if grade else False,
                'over_leave_day': history.over_leave_day if history else 0.0,
            }))
        if lines:
            self.write({'line_ids': lines})
        return True


class BonusCalculate(models.Model):
    _inherit = "ykk.kpi.bonus.calculate"

    def action_load_employee(self):
        """โหลดพนักงานจาก Evaluation (period ตรง + approved)
        และเซ็ต Grade ของบรรทัด = Adjust Grade ของเอกสารนั้น"""
        self.ensure_one()
        if not self.period_id:
            raise UserError(_("Please select a Period first."))
        department_kpis = self.env['ykk.kpi.department.kpi'].search([
            ('period_id', '=', self.period_id.id),
            ('state', '=', 'approved'),
        ])
        seen = set(self.line_ids.mapped('employee_id').ids)
        lines = []
        for kpi in department_kpis:
            if not kpi.employee_id or kpi.employee_id.id in seen:
                continue
            seen.add(kpi.employee_id.id)
            grade = kpi._get_adjust_grade_record()
            lines.append((0, 0, {
                'employee_id': kpi.employee_id.id,
                'grade_id': grade.id if grade else False,
            }))
        if lines:
            self.write({'line_ids': lines})
        return True
