from odoo import models
from odoo.exceptions import UserError


class KpiDepartmentKpi(models.Model):
    _inherit = "ykk.kpi.department.kpi"

    def action_update_from_annual(self):
        """คัดลอกบรรทัดจาก KPI/Goal Setting ไปยัง Interview, Performance,
        Role และ Behavior โดยไม่แก้ไขรายการใน tab Attitude"""
        self.ensure_one()
        if not self.annual_id:
            raise UserError("Please select an KPI/Goal Setting before updating.")

        annual = self.annual_id

        # Interview Performance และ Performance Evaluation ใช้ข้อมูลชุดเดียวกัน
        # จาก Performance ของ KPI/Goal Setting แต่สร้างเป็นคนละบรรทัด เพื่อให้
        # คะแนนและความคิดเห็นของแต่ละ tab แยกจากกัน
        self.interview_line_ids = [(5, 0, 0)] + [
            (0, 0, {
                "goal_id": line.goal_id.id,
                "achievement_criteria": line.achievement_criteria,
                "weight": line.weight,
            })
            for line in annual.performance_line_ids
        ]

        self.performance_line_ids = [(5, 0, 0)] + [
            (0, 0, {
                "goal_id": line.goal_id.id,
                "achievement_criteria": line.achievement_criteria,
                "weight": line.weight,
            })
            for line in annual.performance_line_ids
        ]

        # Role / Behavior — ใช้ name (Char)
        self.role_line_ids = [(5, 0, 0)] + [
            (0, 0, {
                "name": line.name,
                "achievement_criteria": line.achievement_criteria,
                "weight": line.weight,
            })
            for line in annual.role_line_ids
        ]
        self.behavior_line_ids = [(5, 0, 0)] + [
            (0, 0, {
                "name": line.name,
                "achievement_criteria": line.achievement_criteria,
                "weight": line.weight,
            })
            for line in annual.behavior_line_ids
        ]
