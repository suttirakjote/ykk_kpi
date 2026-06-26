# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError

# Single source of truth for grade options. Reuse everywhere.
GRADE_SELECTION = [
    ('A', 'A'),
    ('B', 'B'),
    ('C', 'C'),
    ('D', 'D'),
    ('E', 'E'),
]


class KpiAdjustment(models.Model):
    _name = 'kpi.adjustment'
    _description = 'KPI Grade Adjustment'
    _inherit = ['mail.thread']
    _order = 'create_date desc'

    name = fields.Char(
        default=lambda self: _('New'), copy=False, readonly=True)
    period_id = fields.Many2one(
        'ykk.kpi.period', string='KPI Period', required=True, tracking=True)
    level_id = fields.Many2one(
        'ykk.kpi.level', string='Job Level', tracking=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
    ], default='draft', required=True, tracking=True)
    line_ids = fields.One2many(
        'kpi.adjustment.line', 'adjustment_id', string='Lines')
    company_id = fields.Many2one(
        'res.company', default=lambda self: self.env.company)

    changed_count = fields.Integer(
        compute='_compute_changed_count', string='Changed')

    department_kpi_count = fields.Integer(
        compute='_compute_department_kpi_count', string='Department KPI')

    @api.depends('line_ids.is_changed')
    def _compute_changed_count(self):
        for rec in self:
            rec.changed_count = len(rec.line_ids.filtered('is_changed'))

    @api.depends('line_ids.department_kpi_id')
    def _compute_department_kpi_count(self):
        for rec in self:
            rec.department_kpi_count = len(rec.line_ids.mapped('department_kpi_id'))

    def action_view_department_kpi(self):
        """Smart button: เปิดเอกสาร Department KPI ที่ถูกอ้างอิงในบรรทัด"""
        self.ensure_one()
        kpis = self.line_ids.mapped('department_kpi_id')
        action = {
            'type': 'ir.actions.act_window',
            'name': _('Department KPI'),
            'res_model': 'ykk.kpi.department.kpi',
            'domain': [('id', 'in', kpis.ids)],
            'view_mode': 'list,form',
        }
        if len(kpis) == 1:
            action.update({'view_mode': 'form', 'res_id': kpis.id})
        return action

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'kpi.adjustment') or _('New')
        return super().create(vals_list)

    def action_populate_employees(self):
        """โหลดข้อมูลจากเอกสาร Department KPI ที่:
        - period_id ตรงกับ KPI Period ของเอกสารนี้
        - status = evaluated
        แล้วเอา Overall Grade ของแต่ละเอกสารมาเป็น current_grade"""
        self.ensure_one()
        if not self.period_id:
            raise UserError(_("Please select a KPI Period first."))

        domain = [
            ('period_id', '=', self.period_id.id),
            ('state', '=', 'evaluated'),
        ]
        # เงื่อนไขเพิ่ม: ต้องเป็น Job Level เดียวกัน (ถ้าระบุไว้)
        if self.level_id:
            domain.append(('level_id', '=', self.level_id.id))
        department_kpis = self.env['ykk.kpi.department.kpi'].search(domain)

        seen = set(self.line_ids.mapped('employee_id').ids)
        lines = []
        for kpi in department_kpis:
            if not kpi.employee_id or kpi.employee_id.id in seen:
                continue
            seen.add(kpi.employee_id.id)
            # current_grade / new_grade คำนวณเองจาก department_kpi_id (Document Ref)
            lines.append((0, 0, {
                'employee_id': kpi.employee_id.id,
                'department_kpi_id': kpi.id,
            }))
        if lines:
            self.write({'line_ids': lines})
        return True

    def action_confirm(self):
        for rec in self:
            rec.line_ids._create_history()
            # push new grade back to employee master
            for line in rec.line_ids:
                line.employee_id.kpi_current_grade = line.new_grade
            rec.state = 'confirmed'

    def action_draft(self):
        self.state = 'draft'


class KpiAdjustmentLine(models.Model):
    _name = 'kpi.adjustment.line'
    _description = 'KPI Grade Adjustment Line'
    _order = 'department_id, employee_id'

    adjustment_id = fields.Many2one(
        'kpi.adjustment', required=True, ondelete='cascade')
    employee_id = fields.Many2one(
        'hr.employee', string='Employee', required=True)
    department_kpi_id = fields.Many2one(
        'ykk.kpi.department.kpi', string='Document Ref')
    department_id = fields.Many2one(
        related='employee_id.department_id', store=True, string='Department')
    period_id = fields.Many2one(
        related='adjustment_id.period_id', store=True)

    # Current Grade = Overall Grade ของเอกสาร Department KPI (Document Ref)
    current_grade = fields.Selection(
        GRADE_SELECTION, string='Current Grade',
        compute='_compute_current_grade', store=True, readonly=True)
    # New Grade = เกรดใหม่ที่ถูกปรับ (default ตาม Current Grade แต่แก้ไขได้)
    new_grade = fields.Selection(
        GRADE_SELECTION, string='New Grade',
        compute='_compute_new_grade', store=True, readonly=False)

    is_changed = fields.Boolean(
        compute='_compute_is_changed', store=True, string='Changed')
    history_ids = fields.One2many(
        'kpi.grade.history', 'line_id', string='History')

    @api.depends('department_kpi_id', 'department_kpi_id.overall_grade_id')
    def _compute_current_grade(self):
        valid = dict(GRADE_SELECTION)
        for line in self:
            grade_name = line.department_kpi_id.overall_grade_id.name
            line.current_grade = grade_name if grade_name in valid else False

    @api.depends('current_grade')
    def _compute_new_grade(self):
        for line in self:
            if not line.new_grade:
                line.new_grade = line.current_grade

    @api.depends('current_grade', 'new_grade')
    def _compute_is_changed(self):
        for line in self:
            line.is_changed = bool(
                line.new_grade and line.new_grade != line.current_grade)

    def _create_history(self):
        """Write a history record for every line whose grade actually changed."""
        History = self.env['kpi.grade.history']
        for line in self:
            if line.is_changed:
                History.create({
                    'line_id': line.id,
                    'employee_id': line.employee_id.id,
                    'period_id': line.period_id.id,
                    'old_grade': line.current_grade,
                    'new_grade': line.new_grade,
                })
