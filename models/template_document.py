from markupsafe import Markup

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools import format_date

THAI_MONTHS = [
    "มกราคม", "กุมภาพันธ์", "มีนาคม", "เมษายน", "พฤษภาคม", "มิถุนายน",
    "กรกฎาคม", "สิงหาคม", "กันยายน", "ตุลาคม", "พฤศจิกายน", "ธันวาคม",
]


def thai_date(date):
    """วันที่แบบไทย พ.ศ. เช่น 27 พฤษภาคม 2569"""
    if not date:
        return ""
    return "%d %s %d" % (date.day, THAI_MONTHS[date.month - 1], date.year + 543)


def money_text(value):
    return "{:,.2f}".format(value or 0.0)


def number_text(value):
    """ตัวเลขแบบตัดศูนย์ท้าย ใช้กับ % และจำนวนวัน เช่น 4, 4.5"""
    return "%g" % (value or 0.0)


# เนื้อหาเริ่มต้น = เอกสารแจ้งการปรับค่าจ้างฯ ตามแบบฟอร์มของบริษัท
# ผู้ใช้แก้ไขได้เองทั้งหมดในแท็บ Document Context
# ค่าที่ดึงจากระบบใช้ <t t-out="object.<field>"/> เป็น placeholder
DEFAULT_BODY_HTML = """
<p style="text-align:right;">วันที่ <t t-out="object.generate_date_th">วันที่</t></p>
<p><strong>เรื่อง</strong><span style="display:inline-block;width:40px;"/>แจ้งการปรับค่าจ้าง และผลการประเมินการปฏิบัติงานประจำปี <t t-out="object.year_th">ปี</t></p>
<p><strong>เรียน</strong><span style="display:inline-block;width:40px;"/><t t-out="object.employee_thai_name">ชื่อพนักงาน</t> <t t-out="object.employee_code">รหัส</t></p>
<p>ขั้นตำแหน่ง<span style="display:inline-block;width:20px;"/><t t-out="object.level_code">รหัสระดับ</t> <t t-out="object.level_name">ระดับ</t></p>
<p style="text-indent:60px;">
    บริษัทวายเคเค (ประเทศไทย) จำกัด ขอแจ้งให้ท่านทราบผลประเมินการปฏิบัติงานในปีที่ผ่านมา
    โดยผลการประเมินของท่านในปีนี้ ได้ระดับ <t t-out="object.grade_name">เกรด</t>
</p>
<p style="text-indent:60px;">
    ทั้งนี้ บริษัทฯ ได้ปรับค่าจ้างของท่าน จากเดิมอัตรา
    <strong><t t-out="object.current_salary_text">0.00</t> <t t-out="object.salary_unit">บาท</t></strong>
    เป็นค่าจ้างใหม่อัตรา
    <strong><t t-out="object.new_salary_text">0.00</t> <t t-out="object.salary_unit">บาท</t></strong>
    โดยคณะกรรมการผู้บริหารพิจารณาปรับขึ้นค่าจ้างประจำปีงบประมาณ <t t-out="object.year_th">ปี</t>
    ค่ากลางอยู่ที่ <strong><t t-out="object.increase_percent_text">0</t>%</strong>
    อย่างไรก็ตามหลักเกณฑ์การปรับค่าจ้างจะขึ้นอยู่กับโครงสร้างเงินเดือนแต่ละขั้นตำแหน่ง
    ผลการประเมินการปฏิบัติงาน และเวลาทำงานของแต่ละบุคคล เป็นไปตามประกาศระบบค่าตอบแทน
    และแนวทางในการปรับอัตราเงินเดือนในระบบบุคลากรแบบใหม่ เลขที่ เอ.ซี. 004/2568
    ลงวันที่ 12 มีนาคม 2568
</p>
<p style="text-indent:60px;">ซึ่งมีรายละเอียดการปรับค่าจ้างดังนี้</p>
<table style="width:100%;border-collapse:collapse;text-align:center;">
    <thead>
        <tr>
            <th style="border:1px solid #000;padding:6px;">ฐานในการคำนวณ(บาท)</th>
            <th style="border:1px solid #000;padding:6px;">ปรับขึ้นตามร้อยละค่ากลาง</th>
            <th style="border:1px solid #000;padding:6px;">
                บวกเพิ่ม / หัก เกรด<br/>( Merit <t t-out="object.merit_text">0</t> % )
            </th>
            <th style="border:1px solid #000;padding:6px;">
                หัก วันลาเกิน<br/>(Over leave <t t-out="object.over_leave_day_text">0</t> วัน)<br/>
                ( Att <t t-out="object.att_text">0</t> %)
            </th>
            <th style="border:1px solid #000;padding:6px;">เงินปรับพิเศษ<br/>(Premium)</th>
            <th style="border:1px solid #000;padding:6px;">ฐานใหม่(บาท)</th>
        </tr>
    </thead>
    <tbody>
        <tr>
            <td style="border:1px solid #000;padding:6px;"><t t-out="object.current_salary_text">0.00</t></td>
            <td style="border:1px solid #000;padding:6px;"><t t-out="object.increase_new_salary_year_text">0.00</t></td>
            <td style="border:1px solid #000;padding:6px;"><t t-out="object.plus_minus_text">0.00</t></td>
            <td style="border:1px solid #000;padding:6px;"><t t-out="object.over_leave_baht_text">0.00</t></td>
            <td style="border:1px solid #000;padding:6px;"><t t-out="object.premium_text">0.00</t></td>
            <td style="border:1px solid #000;padding:6px;"><t t-out="object.new_salary_text">0.00</t></td>
        </tr>
    </tbody>
</table>
<p style="text-indent:60px;">
    โดยการปรับค่าจ้างใหม่นี้ มีผลตั้งแต่วันที่ <t t-out="object.effective_date_th">วันที่</t> เป็นต้นไป
</p>
<p style="text-indent:60px;">
    บริษัทฯ หวังเป็นอย่างยิ่งว่า ท่านจะปฏิบัติงานในหน้าที่อย่างเต็มความรู้ความสามารถ
    เพื่อความเจริญก้าวหน้าของตัวท่านเองและของบริษัทฯ ต่อไป
</p>
"""

DEFAULT_FOOTER_HTML = """
<p style="text-align:center;margin-top:40px;">จึงแจ้งมาเพื่อทราบ</p>
<p style="text-align:center;margin-top:80px;">( นางสาวสุพัตรา แซ่ลี้ )</p>
<p style="text-align:center;">แผนกทรัพยากรบุคคล</p>
"""


class TemplateDocument(models.Model):
    _name = "ykk.kpi.template.document"
    _description = "Template Document"
    _inherit = ["mail.render.mixin"]
    _order = "id desc"

    name = fields.Char(string="Reference", default="New", readonly=True, copy=False)
    generate_date = fields.Date(
        string="Generate Date",
        default=fields.Date.context_today,
        required=True,
        help="วันที่ที่ใช้ Generate เอกสาร - แสดงเป็นวันที่หัวจดหมาย",
    )
    effective_date = fields.Date(
        string="Effective Date",
        help="วันที่การปรับค่าจ้างใหม่มีผลบังคับใช้",
    )
    period_id = fields.Many2one("ykk.kpi.period", string="Period")
    responsible_id = fields.Many2one(
        "res.users", string="Responsible", default=lambda self: self.env.user
    )
    company_id = fields.Many2one(
        "res.company", string="Company", required=True,
        default=lambda self: self.env.company,
    )
    salary_calculate_id = fields.Many2one(
        "ykk.kpi.salary.calculate", string="Salary Calculate"
    )
    bonus_calculate_id = fields.Many2one(
        "ykk.kpi.bonus.calculate", string="Bonus Calculate"
    )
    state = fields.Selection(
        [("draft", "Draft"), ("generated", "Generated")],
        string="Status", default="draft", required=True, copy=False,
    )
    line_ids = fields.One2many(
        "ykk.kpi.template.document.line", "document_id", string="Employees"
    )
    employee_count = fields.Integer(
        string="Employee Count", compute="_compute_employee_count"
    )

    # --- ตั้งค่าหน้ากระดาษ ---
    # ระยะขอบซ้าย/ขวา/บน/ล่าง ตั้งที่ Paper Format "YKK Letter (A4)"
    font_size = fields.Integer(
        string="Font Size (pt)", default=14,
        help="ขนาดตัวอักษรในเอกสาร PDF",
    )
    show_company_header = fields.Boolean(
        string="Show Company Header", default=False,
        help="แสดงโลโก้และชื่อบริษัทที่หัวกระดาษ - ปิดไว้ถ้าพิมพ์ลงกระดาษหัวจดหมายอยู่แล้ว",
    )
    show_page_number = fields.Boolean(
        string="Show Page Number", default=False,
        help="แสดงเลขหน้าที่ท้ายกระดาษ",
    )

    # --- Document Context (แท็บที่ 2) -------------------------------------
    # doc_title เป็น Char -> engine inline_template -> ใช้ {{ object.<field> }}
    # body/footer เป็น Html -> engine qweb -> ใช้ <t t-out="object.<field>"/>
    doc_title = fields.Char(
        string="Document Title",
        help="หัวเรื่องกลางหน้ากระดาษ - เว้นว่างไว้ได้ถ้าใส่หัวเรื่องไว้ใน Body แล้ว",
    )
    body_html = fields.Html(
        string="Body", render_engine="qweb", sanitize=False,
        default=lambda self: Markup(DEFAULT_BODY_HTML),
    )
    footer_html = fields.Html(
        string="Footer", render_engine="qweb", sanitize=False,
        default=lambda self: Markup(DEFAULT_FOOTER_HTML),
    )
    preview_html = fields.Html(
        string="Preview", compute="_compute_preview_html", sanitize=False
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", "New") == "New":
                vals["name"] = self.env["ir.sequence"].next_by_code(
                    "ykk.kpi.template.document") or "New"
        return super().create(vals_list)

    # ------------------------------------------------------------------
    # Rendering (ใช้เอนจินเดียวกับ Email Template)
    # ------------------------------------------------------------------
    def _compute_render_model(self):
        """Context ถูก render โดยอ้าง object = บรรทัดพนักงาน 1 คน"""
        self.render_model = "ykk.kpi.template.document.line"

    RENDER_FIELDS = ("doc_title", "body_html", "footer_html")

    def _render_document_fields(self, lines=None):
        """Render ทุก field ของ Context สำหรับแต่ละบรรทัดพนักงาน

        :return dict: {line_id: {field: rendered value}}
        """
        self.ensure_one()
        lines = self.line_ids if lines is None else lines
        res_ids = [line.id for line in lines if isinstance(line.id, int)]
        values = {res_id: {} for res_id in res_ids}
        if not res_ids:
            return values
        for field_name in self.RENDER_FIELDS:
            for res_id, rendered in self._render_field(field_name, res_ids).items():
                values[res_id][field_name] = rendered
        return values

    @api.depends("doc_title", "body_html", "footer_html", "line_ids")
    def _compute_preview_html(self):
        """ตัวอย่างเอกสารของพนักงานคนแรก - ช่วยตรวจ placeholder ก่อนพิมพ์จริง"""
        for record in self:
            line = record.line_ids[:1]
            if not line or not isinstance(line.id, int):
                record.preview_html = Markup(
                    '<div class="text-muted">เพิ่มพนักงานในแท็บ Employees '
                    'และบันทึกเอกสารก่อน จึงจะแสดงตัวอย่างได้</div>'
                )
                continue
            try:
                rendered = record._render_document_fields(line).get(line.id, {})
            except Exception as error:  # noqa: BLE001 - แสดง error ให้ผู้ใช้แก้ template
                # ตัด template source ที่ Odoo แนบมาท้าย error ออก ให้เหลือแต่สาเหตุ
                message = str(error).split("Template Source")[0].strip()
                record.preview_html = Markup(
                    '<div class="alert alert-danger">'
                    '<strong>Render ไม่สำเร็จ</strong><br/>%s<br/><br/>'
                    'ตรวจว่า placeholder ที่ใช้ในแท็บ Document Context มีอยู่จริง '
                    '(ดูรายชื่อในกล่องสีฟ้าใต้ช่อง Footer) '
                    'หรือกดปุ่ม <strong>Reset Context to Default</strong> '
                    'เพื่อคืนค่าเป็นแบบฟอร์มมาตรฐาน</div>'
                ) % message
                continue
            title = rendered.get("doc_title")
            record.preview_html = Markup(
                '<div class="border rounded p-4 bg-white">%s%s%s</div>'
            ) % (
                Markup('<h4 class="text-center">%s</h4>') % title if title else "",
                Markup(rendered.get("body_html") or ""),
                Markup(rendered.get("footer_html") or ""),
            )

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------
    @api.depends("line_ids")
    def _compute_employee_count(self):
        for record in self:
            record.employee_count = len(record.line_ids)

    def action_load_employees(self):
        """สร้างบรรทัดพนักงานจาก Salary Calculate / Bonus Calculate ที่เลือก
        (บรรทัดเดิมจะถูกแทนที่ทั้งหมด ตัวเลขแต่ละช่องคำนวณเองในบรรทัด)"""
        self.ensure_one()
        if not self.salary_calculate_id and not self.bonus_calculate_id:
            raise UserError(
                _("Please select a Salary Calculate or a Bonus Calculate first.")
            )
        employees = (
            self.salary_calculate_id.line_ids.mapped("employee_id")
            | self.bonus_calculate_id.line_ids.mapped("employee_id")
        )
        if not employees:
            raise UserError(_("ไม่พบพนักงานในเอกสาร Salary / Bonus Calculate ที่เลือก"))
        Line = self.env["ykk.kpi.template.document.line"]
        self.line_ids = [(5, 0, 0)] + [
            (0, 0, dict(
                Line._values_from_calculate(
                    employee, self.salary_calculate_id, self.bonus_calculate_id
                ),
                employee_id=employee.id,
            ))
            for employee in employees
        ]
        return True

    def action_print(self):
        self.ensure_one()
        if not self.line_ids:
            raise UserError(_("กรุณาเพิ่มพนักงานในแท็บ Employees ก่อนพิมพ์เอกสาร"))
        self.state = "generated"
        return self.env.ref("ykk_kpi.action_report_template_document").report_action(self)

    def action_draft(self):
        self.write({"state": "draft"})

    def action_reset_context(self):
        """คืนค่า Context กลับเป็นแบบฟอร์มมาตรฐาน
        ใช้เมื่อแก้ template แล้วพัง หรืออยากได้แบบฟอร์มล่าสุดของระบบ"""
        self.write({
            "doc_title": False,
            "body_html": Markup(DEFAULT_BODY_HTML),
            "footer_html": Markup(DEFAULT_FOOTER_HTML),
        })
        return True


class TemplateDocumentLine(models.Model):
    _name = "ykk.kpi.template.document.line"
    _description = "Template Document Line"
    _order = "document_id, id"

    document_id = fields.Many2one(
        "ykk.kpi.template.document", string="Template Document",
        required=True, ondelete="cascade",
    )
    employee_id = fields.Many2one("hr.employee", string="Employee", required=True)

    # --- ข้อมูลพนักงาน (ใช้เป็น placeholder ในเอกสาร) ---
    employee_name = fields.Char(
        string="Employee Name", related="employee_id.name", readonly=True
    )
    employee_thai_name = fields.Char(
        string="Thai Name", related="employee_id.ykk_thai_full_name", readonly=True
    )
    employee_code = fields.Char(
        string="Employee Code", related="employee_id.ykk_employee_code", readonly=True
    )
    department_id = fields.Many2one(
        "hr.department", string="Department",
        related="employee_id.department_id", readonly=True,
    )
    department_name = fields.Char(
        string="Department Name", related="employee_id.department_id.name", readonly=True
    )
    level_id = fields.Many2one(
        "ykk.kpi.level", string="Job Level",
        related="employee_id.ykk_kpi_level_id", readonly=True,
    )
    level_code = fields.Char(
        string="Level Code", related="employee_id.ykk_kpi_level_id.code", readonly=True
    )
    level_name = fields.Char(
        string="Level Name", related="employee_id.ykk_kpi_level_id.name", readonly=True
    )
    period_name = fields.Char(
        string="Period Name", related="document_id.period_id.name", readonly=True
    )
    responsible_name = fields.Char(
        string="Responsible Name", related="document_id.responsible_id.name", readonly=True
    )
    salary_unit = fields.Char(
        string="Salary Unit", compute="_compute_salary_unit",
        help="บาท/เดือน หรือ บาท/วัน ตามประเภทพนักงาน",
    )

    # --- วันที่ในรูปแบบไทย (พ.ศ.) ---
    generate_date_th = fields.Char(
        string="Generate Date (TH)", compute="_compute_date_texts"
    )
    effective_date_th = fields.Char(
        string="Effective Date (TH)", compute="_compute_date_texts"
    )
    year_th = fields.Char(string="Year (TH)", compute="_compute_date_texts")
    # วันที่ตามภาษาของผู้ใช้ (ค.ศ.) - เผื่อ template ที่ไม่ต้องการ พ.ศ.
    generate_date_text = fields.Char(
        string="Generate Date Text", compute="_compute_date_texts"
    )

    # --- ตัวเลขจาก Salary Calculate / Bonus Calculate ---
    # เก็บเป็นค่านิ่ง (ไม่ compute) เติมตอน Load Employees / เลือกพนักงาน
    # ตัวเลขบนจดหมายที่พิมพ์ไปแล้วจึงไม่เปลี่ยนตามเอกสารคำนวณที่ถูกแก้ทีหลัง
    grade_id = fields.Many2one("ykk.kpi.grade", string="Grade")
    grade_name = fields.Char(string="Grade Name", related="grade_id.name", readonly=True)
    current_salary = fields.Float(string="Current Salary")
    increase_percent = fields.Float(string="Increase %")
    increase_new_salary_year = fields.Float(string="Increase new Salary Year")
    merit = fields.Float(string="Merit %")
    att = fields.Float(string="Att %")
    plus_minus = fields.Float(string="+/- Grade")
    over_leave_day = fields.Float(string="Over Leave Day")
    over_leave_baht = fields.Float(string="Over Leave Baht")
    # ไม่มีในระบบคำนวณ - กรอกเองต่อพนักงาน
    premium = fields.Float(string="Premium")
    final_increase = fields.Float(string="Final Increase Salary")
    new_salary = fields.Float(string="New Salary")
    new_salary_month = fields.Float(string="New Salary Month")
    bonus = fields.Float(string="Bonus")
    bonus_grd = fields.Float(string="Bonus(GRD)")
    net_pay = fields.Float(string="Net Pay")

    # --- ตัวเลขในรูปข้อความ สำหรับใช้เป็น placeholder ในเอกสาร ---
    MONEY_FIELDS = (
        "current_salary", "increase_new_salary_year", "plus_minus",
        "over_leave_baht", "premium", "final_increase", "new_salary",
        "new_salary_month", "bonus", "bonus_grd", "net_pay",
    )
    NUMBER_FIELDS = ("increase_percent", "merit", "att", "over_leave_day")

    current_salary_text = fields.Char(compute="_compute_amount_texts", string="Current Salary Text")
    increase_new_salary_year_text = fields.Char(compute="_compute_amount_texts", string="Increase Year Text")
    plus_minus_text = fields.Char(compute="_compute_amount_texts", string="+/- Grade Text")
    over_leave_baht_text = fields.Char(compute="_compute_amount_texts", string="Over Leave Baht Text")
    premium_text = fields.Char(compute="_compute_amount_texts", string="Premium Text")
    final_increase_text = fields.Char(compute="_compute_amount_texts", string="Final Increase Text")
    new_salary_text = fields.Char(compute="_compute_amount_texts", string="New Salary Text")
    new_salary_month_text = fields.Char(compute="_compute_amount_texts", string="New Salary Month Text")
    bonus_text = fields.Char(compute="_compute_amount_texts", string="Bonus Text")
    bonus_grd_text = fields.Char(compute="_compute_amount_texts", string="Bonus(GRD) Text")
    net_pay_text = fields.Char(compute="_compute_amount_texts", string="Net Pay Text")
    increase_percent_text = fields.Char(compute="_compute_amount_texts", string="Increase % Text")
    merit_text = fields.Char(compute="_compute_amount_texts", string="Merit % Text")
    att_text = fields.Char(compute="_compute_amount_texts", string="Att % Text")
    over_leave_day_text = fields.Char(compute="_compute_amount_texts", string="Over Leave Day Text")

    _sql_constraints = [
        (
            "document_employee_unique",
            "unique(document_id, employee_id)",
            "An employee can only be added once per Template Document.",
        ),
    ]

    @api.model
    def _values_from_calculate(self, employee, salary_calculate, bonus_calculate):
        """ค่าตัวเลขทั้งหมดของพนักงาน 1 คน ดึงจากเอกสารคำนวณที่เลือกไว้"""
        salary = salary_calculate.line_ids.filtered(
            lambda l: l.employee_id == employee)[:1]
        bonus = bonus_calculate.line_ids.filtered(
            lambda l: l.employee_id == employee)[:1]
        return {
            "grade_id": (salary.grade_id or bonus.grade_id).id,
            "current_salary": salary.current_salary or bonus.current_salary,
            "increase_percent": salary.effective_increase_percent,
            "increase_new_salary_year": salary.increase_new_salary_year,
            "merit": salary.merit,
            "att": salary.att,
            "plus_minus": salary.plus_minus,
            "over_leave_day": salary.over_leave_day,
            "over_leave_baht": salary.over_leave_baht,
            "final_increase": salary.increase,
            "new_salary": salary.new_salary,
            "new_salary_month": salary.new_salary_month,
            "bonus": bonus.bonus,
            "bonus_grd": bonus.bonus_grd,
            "net_pay": bonus.net_pay,
        }

    @api.onchange("employee_id")
    def _onchange_employee_id(self):
        """เพิ่มพนักงานเองในตาราง -> ดึงตัวเลขจากเอกสารคำนวณให้อัตโนมัติ"""
        for line in self:
            if not line.employee_id:
                continue
            values = line._values_from_calculate(
                line.employee_id,
                line.document_id.salary_calculate_id,
                line.document_id.bonus_calculate_id,
            )
            for field_name, value in values.items():
                line[field_name] = value

    @api.depends("employee_id.ykk_kpi_employee_type")
    def _compute_salary_unit(self):
        for line in self:
            line.salary_unit = (
                "บาท/วัน" if line.employee_id.ykk_kpi_employee_type == "daily"
                else "บาท/เดือน"
            )

    @api.depends("document_id.generate_date", "document_id.effective_date")
    def _compute_date_texts(self):
        for line in self:
            document = line.document_id
            line.generate_date_th = thai_date(document.generate_date)
            line.effective_date_th = thai_date(document.effective_date)
            line.year_th = (
                str(document.generate_date.year + 543) if document.generate_date else ""
            )
            line.generate_date_text = (
                format_date(self.env, document.generate_date)
                if document.generate_date else ""
            )

    @api.depends(*(MONEY_FIELDS + NUMBER_FIELDS))
    def _compute_amount_texts(self):
        for line in self:
            for field_name in line.MONEY_FIELDS:
                line["%s_text" % field_name] = money_text(line[field_name])
            for field_name in line.NUMBER_FIELDS:
                line["%s_text" % field_name] = number_text(line[field_name])


class ReportTemplateDocument(models.AbstractModel):
    _name = "report.ykk_kpi.report_template_document"
    _description = "Template Document Report"

    @api.model
    def _get_report_values(self, docids, data=None):
        documents = self.env["ykk.kpi.template.document"].browse(docids)
        rendered = {}
        for document in documents:
            rendered.update(document._render_document_fields())
        return {
            "doc_ids": docids,
            "doc_model": "ykk.kpi.template.document",
            "docs": documents,
            "rendered": rendered,
        }
