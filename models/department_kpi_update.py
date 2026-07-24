from odoo import models
from odoo.exceptions import UserError


class KpiDepartmentKpi(models.Model):
    _inherit = "ykk.kpi.department.kpi"

    def action_update_from_annual(self):
        """คัดลอกบรรทัดจาก Annual KPI ที่เลือก มาใส่ใน 4 tab ของ Department KPI
        (ยกเว้น tab Summary). บรรทัดเดิมในแต่ละ tab จะถูกแทนที่ทั้งหมด"""
        self.ensure_one()
        if not self.annual_id:
            raise UserError("Please select an Annual KPI before updating.")

        annual = self.annual_id

        # Performance — ใช้ goal_id (Many2one)
        self.performance_line_ids = [(5, 0, 0)] + [
            (0, 0, {
                "goal_id": line.goal_id.id,
                "achievement_criteria": line.achievement_criteria,
                "weight": line.weight,
            })
            for line in annual.performance_line_ids
        ]

        # Role / Behavior / Attitude — ใช้ name (Char)
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
        self.attitude_line_ids = [(5, 0, 0)] + [
            (0, 0, {
                "name": line.name,
                "achievement_criteria": line.achievement_criteria,
                "weight": line.weight,
            })
            for line in annual.attitude_line_ids
        ]
