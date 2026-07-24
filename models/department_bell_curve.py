import math

from odoo import _, api, fields, models
from odoo.exceptions import UserError


def _probit(p):
    """Inverse of the standard normal CDF (Acklam's rational approximation)."""
    if p <= 0.0:
        return -6.0
    if p >= 1.0:
        return 6.0
    a = [-3.969683028665376e+01, 2.209460984245205e+02, -2.759285104469687e+02,
         1.383577518672690e+02, -3.066479806614716e+01, 2.506628277459239e+00]
    b = [-5.447609879822406e+01, 1.615858368580409e+02, -1.556989798598866e+02,
         6.680131188771972e+01, -1.328068155288572e+01]
    c = [-7.784894002430293e-03, -3.223964580411365e-01, -2.400758277161838e+00,
         -2.549732539343734e+00, 4.374664141464968e+00, 2.938163982698783e+00]
    d = [7.784695709041462e-03, 3.224671290700398e-01, 2.445134137142996e+00,
         3.754408661907416e+00]
    plow = 0.02425
    phigh = 1 - plow
    if p < plow:
        q = math.sqrt(-2 * math.log(p))
        return (((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) / \
               ((((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1)
    if p <= phigh:
        q = p - 0.5
        r = q * q
        return (((((a[0] * r + a[1]) * r + a[2]) * r + a[3]) * r + a[4]) * r + a[5]) * q / \
               (((((b[0] * r + b[1]) * r + b[2]) * r + b[3]) * r + b[4]) * r + 1)
    q = math.sqrt(-2 * math.log(1 - p))
    return -(((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) / \
           ((((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1)


class KpiDepartmentBellCurve(models.Model):
    _name = "ykk.kpi.department.bell.curve"
    _description = "Department Bell Curve"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "id desc"

    name = fields.Char(string="Name", default="New", required=True, readonly=True, copy=False)
    date = fields.Date(string="Date", default=fields.Date.context_today, required=True)
    department_id = fields.Many2one("hr.department", string="Department", required=True, tracking=True)
    period_id = fields.Many2one("ykk.kpi.period", string="Period", required=True, tracking=True)
    company_id = fields.Many2one("res.company", string="Company", required=True, default=lambda self: self.env.company)
    responsible_id = fields.Many2one("res.users", string="Responsible", default=lambda self: self.env.user)

    line_ids = fields.One2many("ykk.kpi.department.bell.curve.line", "bell_curve_id", string="Employees")

    employee_count = fields.Integer(string="Employee Count", compute="_compute_statistics", store=True)
    mean_score = fields.Float(string="Mean", digits="KPI Score", compute="_compute_statistics", store=True)
    std_dev = fields.Float(string="Std Dev", digits="KPI Score", compute="_compute_statistics", store=True)
    bell_curve_svg = fields.Html(string="Bell Curve", compute="_compute_bell_curve", sanitize=False)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", "New") == "New":
                vals["name"] = self.env["ir.sequence"].next_by_code("ykk.kpi.department.bell.curve") or "New"
        return super().create(vals_list)

    # ------------------------------------------------------------------
    # Load data
    # ------------------------------------------------------------------
    def action_load_data(self):
        self.ensure_one()
        if not self.department_id or not self.period_id:
            raise UserError(_("กรุณาเลือก Department และ Period ก่อนกด Load Data"))
        kpis = self.env["ykk.kpi.department.kpi"].search([
            ("department_id", "=", self.department_id.id),
            ("period_id", "=", self.period_id.id),
        ])
        if not kpis:
            raise UserError(_("ไม่พบข้อมูล Department KPI ตามเงื่อนไขที่เลือก"))
        commands = [(5, 0, 0)]
        for kpi in kpis:
            commands.append((0, 0, {
                "department_kpi_id": kpi.id,
                "employee_id": kpi.employee_id.id,
                "group_position_id": kpi.group_position_id.id,
                "level_id": kpi.level_id.id,
                "overall_grade_id": kpi.overall_grade_id.id,
                "document_ref": kpi.name,
                "score": kpi.total_score,
            }))
        self.line_ids = commands
        self._apply_forced_distribution()
        return True

    # ------------------------------------------------------------------
    # Forced distribution (20-60-20 → A/B/C/D/E)
    # ------------------------------------------------------------------
    def _get_distribution_bands(self):
        """Return ordered list of (grade, share_pct), best grade first.

        Read from Relative Adjustment Group (grouped distribution), splitting
        each group's share equally across its grades. Falls back to the
        standard A/B/C/D/E = 10/10/60/10/10 split if nothing is configured.
        """
        bands = []
        groups = self.env["ykk.kpi.relative.adjustment.group"].search(
            [("active", "=", True)], order="sequence, id"
        )
        for group in groups:
            grades = group.grade_ids.sorted(
                key=lambda g: (g.grade_score, g.end_score), reverse=True
            )
            if not grades or not group.distribution:
                continue
            share = group.distribution / len(grades)
            for grade in grades:
                bands.append((grade, share))
        if bands:
            return bands
        Grade = self.env["ykk.kpi.grade"]
        for code, share in [("A", 10.0), ("B", 10.0), ("C", 60.0), ("D", 10.0), ("E", 10.0)]:
            grade = Grade.search(["|", ("code", "=", code), ("name", "=", code)], limit=1)
            if grade:
                bands.append((grade, share))
        return bands

    def _apply_forced_distribution(self):
        for record in self:
            lines = record.line_ids.sorted(key=lambda l: l.score, reverse=True)
            bands = record._get_distribution_bands()
            if not lines or not bands:
                continue
            n = len(lines)
            raw = [share / 100.0 * n for _grade, share in bands]
            counts = [int(math.floor(r)) for r in raw]
            remainder = n - sum(counts)
            order = sorted(range(len(bands)), key=lambda i: raw[i] - counts[i], reverse=True)
            idx = 0
            while remainder > 0 and order:
                counts[order[idx % len(order)]] += 1
                idx += 1
                remainder -= 1
            pos = 0
            for band_index, (grade, _share) in enumerate(bands):
                for _n in range(counts[band_index]):
                    if pos >= n:
                        break
                    lines[pos].new_grade_id = grade.id
                    pos += 1
            while pos < n:
                lines[pos].new_grade_id = bands[-1][0].id
                pos += 1

    # ------------------------------------------------------------------
    # Statistics + bell curve
    # ------------------------------------------------------------------
    @api.depends("line_ids", "line_ids.score")
    def _compute_statistics(self):
        for record in self:
            scores = record.line_ids.mapped("score")
            n = len(scores)
            record.employee_count = n
            if n:
                mean = sum(scores) / n
                variance = sum((s - mean) ** 2 for s in scores) / n
                record.mean_score = mean
                record.std_dev = math.sqrt(variance)
            else:
                record.mean_score = 0.0
                record.std_dev = 0.0

    @api.depends("line_ids", "line_ids.score", "line_ids.new_grade_id", "mean_score", "std_dev")
    def _compute_bell_curve(self):
        for record in self:
            record.bell_curve_svg = record._build_bell_curve_svg()

    def _zone_color(self, index, total):
        """Green (best) → red (worst) hue ramp, index 0 = worst (left)."""
        if total <= 1:
            hue = 130
        else:
            hue = 130.0 * index / (total - 1)
        return "hsl(%d, 70%%, 55%%)" % int(hue)

    def _build_bell_curve_svg(self):
        self.ensure_one()
        scores = self.line_ids.mapped("score")
        n = len(scores)
        if n < 2 or self.std_dev <= 0:
            return (
                '<div style="padding:16px;color:#888;">'
                'ยังไม่มีข้อมูลเพียงพอสำหรับพลอตกราฟ (ต้องมีพนักงานอย่างน้อย 2 คน '
                'และคะแนนต้องมีการกระจายตัว)</div>'
            )
        mean = self.mean_score
        sd = self.std_dev
        bands = self._get_distribution_bands()  # best first
        if not bands:
            return '<div style="padding:16px;color:#888;">ยังไม่ได้ตั้งค่า Grade / Relative Adjustment Group</div>'

        # Layout
        W, H = 820, 440
        ml, mr, mt, mb = 55, 20, 30, 70
        plot_w = W - ml - mr
        plot_h = H - mt - mb
        xmin = mean - 3.6 * sd
        xmax = mean + 3.6 * sd

        def x_to_px(x):
            return ml + (x - xmin) / (xmax - xmin) * plot_w

        def pdf(x):
            return math.exp(-((x - mean) ** 2) / (2 * sd * sd))

        def y_to_px(p):
            return mt + (1 - p) * plot_h

        # Zones from left (worst) to right (best): reverse the band order.
        bottom_bands = list(reversed(bands))  # worst → best
        cum = [0.0]
        for _grade, share in bottom_bands:
            cum.append(cum[-1] + share / 100.0)
        cum[-1] = 1.0
        m = len(bottom_bands)

        parts = []
        parts.append(
            '<svg viewBox="0 0 %d %d" xmlns="http://www.w3.org/2000/svg" '
            'style="width:100%%;max-width:%dpx;height:auto;font-family:sans-serif;">' % (W, H, W)
        )

        # Zone fills under the curve
        for k in range(m):
            grade, share = bottom_bands[k]
            xl = xmin if k == 0 else mean + _probit(cum[k]) * sd
            xr = xmax if k == m - 1 else mean + _probit(cum[k + 1]) * sd
            xl = max(xl, xmin)
            xr = min(xr, xmax)
            if xr <= xl:
                continue
            color = self._zone_color(k, m)
            steps = 24
            pts = ["%.1f,%.1f" % (x_to_px(xl), y_to_px(0))]
            for i in range(steps + 1):
                x = xl + (xr - xl) * i / steps
                pts.append("%.1f,%.1f" % (x_to_px(x), y_to_px(pdf(x))))
            pts.append("%.1f,%.1f" % (x_to_px(xr), y_to_px(0)))
            parts.append(
                '<polygon points="%s" fill="%s" fill-opacity="0.55" stroke="none"/>'
                % (" ".join(pts), color)
            )
            # boundary line (right edge of zone, skip the outer one)
            if k < m - 1:
                bx = x_to_px(xr)
                parts.append(
                    '<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="#fff" '
                    'stroke-width="1" stroke-dasharray="3,3"/>'
                    % (bx, y_to_px(0), bx, mt)
                )
            # zone label (grade + count)
            count = len(self.line_ids.filtered(lambda l, g=grade: l.new_grade_id == g))
            lx = x_to_px((xl + xr) / 2)
            parts.append(
                '<text x="%.1f" y="%.1f" text-anchor="middle" font-size="13" '
                'font-weight="bold" fill="#333">%s</text>'
                % (lx, mt - 8, grade.name or grade.code or "")
            )
            parts.append(
                '<text x="%.1f" y="%.1f" text-anchor="middle" font-size="11" fill="#555">%d</text>'
                % (lx, H - mb + 34, count)
            )

        # Normal curve outline
        curve_pts = []
        for i in range(121):
            x = xmin + (xmax - xmin) * i / 120
            curve_pts.append("%.1f,%.1f" % (x_to_px(x), y_to_px(pdf(x))))
        parts.append(
            '<polyline points="%s" fill="none" stroke="#333" stroke-width="2"/>'
            % " ".join(curve_pts)
        )

        # Baseline / x-axis
        base_y = y_to_px(0)
        parts.append(
            '<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="#333" stroke-width="1"/>'
            % (ml, base_y, W - mr, base_y)
        )

        # Mean line
        mx = x_to_px(mean)
        parts.append(
            '<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="#c00" '
            'stroke-width="1.5" stroke-dasharray="5,3"/>' % (mx, mt, mx, base_y)
        )
        parts.append(
            '<text x="%.1f" y="%.1f" text-anchor="middle" font-size="11" fill="#c00">'
            'Mean %.1f</text>' % (mx, mt - 18, mean)
        )

        # X-axis ticks at mean ± k·sd
        for k in range(-3, 4):
            x = mean + k * sd
            if x < xmin or x > xmax:
                continue
            px = x_to_px(x)
            parts.append(
                '<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="#999" stroke-width="1"/>'
                % (px, base_y, px, base_y + 5)
            )
            parts.append(
                '<text x="%.1f" y="%.1f" text-anchor="middle" font-size="10" fill="#666">%.0f</text>'
                % (px, base_y + 18, x)
            )

        # Employee score markers on the baseline
        for score in scores:
            sx = x_to_px(min(max(score, xmin), xmax))
            parts.append(
                '<circle cx="%.1f" cy="%.1f" r="3" fill="#1f77b4" fill-opacity="0.7"/>'
                % (sx, base_y)
            )

        parts.append(
            '<text x="%.1f" y="%.1f" text-anchor="middle" font-size="11" fill="#888">'
            'จำนวนพนักงานต่อเกรด (Count)</text>' % (ml + plot_w / 2, H - 6)
        )
        parts.append("</svg>")
        return "".join(parts)


class KpiDepartmentBellCurveLine(models.Model):
    _name = "ykk.kpi.department.bell.curve.line"
    _description = "Department Bell Curve Line"
    _order = "score desc, id"

    bell_curve_id = fields.Many2one(
        "ykk.kpi.department.bell.curve", string="Bell Curve", required=True, ondelete="cascade"
    )
    department_kpi_id = fields.Many2one("ykk.kpi.department.kpi", string="Department KPI Ref")
    employee_id = fields.Many2one("hr.employee", string="Employee Name")
    group_position_id = fields.Many2one("ykk.kpi.group.position", string="Group Position")
    level_id = fields.Many2one("ykk.kpi.level", string="Job Level")
    overall_grade_id = fields.Many2one("ykk.kpi.grade", string="Overall Grade")
    document_ref = fields.Char(string="Document Ref")
    score = fields.Float(string="Score", digits="KPI Score")
    new_grade_id = fields.Many2one("ykk.kpi.grade", string="Bell Curve Grade")
