from odoo import api, fields, models


class RelativeAdjustmentGroup(models.Model):
    _name = "ykk.kpi.relative.adjustment.group"
    _description = "Relative Adjustment Group"
    _order = "sequence, id"

    sequence = fields.Integer(string="Sequence", default=10)
    name = fields.Char(string="Name", required=True)
    grade_ids = fields.Many2many(
        "ykk.kpi.grade",
        "ykk_kpi_rel_adj_group_grade_rel",
        "group_id",
        "grade_id",
        string="Grade",
    )
    # Distribution % (ส่วนสีน้ำเงิน) - กรอกเอง ใช้เป็นเป้าหมายการกระจาย
    distribution = fields.Float(string="Distribution (%)")
    # ป้ายชื่อสำหรับ Grade Board เช่น "Group1(A,B)"
    board_label = fields.Char(compute="_compute_board_label")

    @api.depends("name", "grade_ids", "grade_ids.name")
    def _compute_board_label(self):
        for rec in self:
            grades = ",".join(sorted(rec.grade_ids.mapped("name")))
            rec.board_label = "%s(%s)" % (rec.name or "", grades) if grades else (rec.name or "")
    company_id = fields.Many2one(
        "res.company",
        string="Company",
        required=True,
        default=lambda self: self.env.company,
    )
    active = fields.Boolean(string="Active", default=True)
