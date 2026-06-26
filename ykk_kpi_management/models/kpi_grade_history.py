# -*- coding: utf-8 -*-
from odoo import models, fields

GRADE_SELECTION = [
    ('A', 'A'), ('B', 'B'), ('C', 'C'), ('D', 'D'), ('E', 'E'),
]


class KpiGradeHistory(models.Model):
    _name = 'kpi.grade.history'
    _description = 'KPI Grade History'
    _order = 'create_date desc'

    line_id = fields.Many2one(
        'kpi.adjustment.line', string='Adjustment Line', ondelete='cascade')
    employee_id = fields.Many2one('hr.employee', required=True, index=True)
    period_id = fields.Many2one('ykk.kpi.period', required=True)
    old_grade = fields.Selection(GRADE_SELECTION, string='Old Grade')
    new_grade = fields.Selection(GRADE_SELECTION, string='New Grade')
    changed_by = fields.Many2one(
        'res.users', default=lambda self: self.env.user, readonly=True)


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    kpi_current_grade = fields.Selection(
        GRADE_SELECTION, string='KPI Current Grade')
    kpi_history_ids = fields.One2many(
        'kpi.grade.history', 'employee_id', string='KPI Grade History')
