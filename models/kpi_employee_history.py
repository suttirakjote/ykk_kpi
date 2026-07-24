from odoo import fields, models


class KpiEmployeeHistory(models.Model):
    _name = "ykk.kpi.employee.history"
    _description = "KPI Employee History"
    _order = "year desc, id desc"

    employee_id = fields.Many2one(
        "hr.employee", string="Employee", required=True, ondelete="cascade"
    )
    year = fields.Integer(string="Year")          # คริสศักราช (ค.ศ.)
    date_att = fields.Float(string="Date ATT")
    over_leave_day = fields.Float(string="Over Leave Day")
    update = fields.Datetime(string="Update")     # วัน-เวลาที่ upload ไฟล์เข้าระบบ
