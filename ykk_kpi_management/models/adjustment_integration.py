# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class KpiDepartmentKpi(models.Model):
    _inherit = "ykk.kpi.department.kpi"

    # Adjust Grade = New Grade จาก KPI Grade Adjustments
    #   - ถ้า Changed = True  -> ใช้ New Grade
    #   - ถ้า Changed = False -> ใช้ Current Grade
    adjust_grade = fields.Char(
        string="Adjust Grade", compute="_compute_adjust_grade")

    def _compute_adjust_grade(self):
        AdjLine = self.env['kpi.adjustment.line']
        for rec in self:
            grade = False
            if rec.id:
                line = AdjLine.search(
                    [('department_kpi_id', '=', rec.id)],
                    order='id desc', limit=1)
                if line:
                    grade = line.new_grade if line.is_changed else line.current_grade
            rec.adjust_grade = grade

    def _get_adjust_grade_record(self):
        """แปลง Adjust Grade (ตัวอักษร A-E) เป็น record ykk.kpi.grade ตาม name"""
        self.ensure_one()
        if not self.adjust_grade:
            return self.env['ykk.kpi.grade']
        return self.env['ykk.kpi.grade'].search([
            ('name', '=', self.adjust_grade),
            ('company_id', '=', self.company_id.id),
        ], limit=1)


class SalaryCalculate(models.Model):
    _inherit = "ykk.kpi.salary.calculate"

    def action_load_employee(self):
        """โหลดพนักงานจาก Department KPI (period ตรง + evaluated)
        และเซ็ต Grade ของบรรทัด = Adjust Grade ของเอกสารนั้น"""
        self.ensure_one()
        if not self.period_id:
            raise UserError(_("Please select a Period first."))
        department_kpis = self.env['ykk.kpi.department.kpi'].search([
            ('period_id', '=', self.period_id.id),
            ('state', '=', 'evaluated'),
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


class BonusCalculate(models.Model):
    _inherit = "ykk.kpi.bonus.calculate"

    def action_load_employee(self):
        """โหลดพนักงานจาก Department KPI (period ตรง + evaluated)
        และเซ็ต Grade ของบรรทัด = Adjust Grade ของเอกสารนั้น"""
        self.ensure_one()
        if not self.period_id:
            raise UserError(_("Please select a Period first."))
        department_kpis = self.env['ykk.kpi.department.kpi'].search([
            ('period_id', '=', self.period_id.id),
            ('state', '=', 'evaluated'),
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
