# Salary Calculate — Developer Guide

เอกสารนี้สรุปฟีเจอร์ **Salary Calculate** (การคำนวณปรับขึ้นเงินเดือนตามผล KPI) ที่พัฒนาเพิ่มในโมดูล `ykk_kpi_management`
สำหรับ developer ที่จะเข้ามาดูแล/พัฒนาต่อ

> **คอนเซปต์การพัฒนา:** โค้ดทั้งหมดถูกเพิ่มแบบ "ไม่แก้ไฟล์ของ dev หลักโดยตรง"
> ใช้ `_inherit` (extend model เดิม) + inherited view (`xpath` / `position`) เป็นไฟล์แยกชื่อ `*_extend.py` / `*_extend_views.xml`

---

## 1. ภาพรวมเมนู

```
KPI Management
└── Calculate (เมนูใหม่)
    └── Salary Calculate   → action_salary_calculate  (list, form)
```

- Top menu `menu_ykk_kpi_calculate` (sequence 30, อยู่ก่อน Configuration)
- เอกสาร 1 ใบ = 1 รอบการคำนวณ มีหลายบรรทัด (1 บรรทัด = พนักงาน 1 คน)

---

## 2. โครงสร้าง Model

ไฟล์หลัก: [`models/salary_calculate.py`](models/salary_calculate.py)

### 2.1 Header — `ykk.kpi.salary.calculate`

| Field | Type | คำอธิบาย |
|-------|------|----------|
| `name` | Char (readonly) | เลขที่เอกสาร running จาก `ir.sequence` (ดู §5) |
| `period_id` | M2o `ykk.kpi.period` | รอบประเมิน |
| `responsible_id` | M2o `res.users` | ผู้รับผิดชอบ default = user ที่ login (แก้ได้) |
| `increase_percent` | Float | **Increase new %** — อัตราขึ้นเงินเดือนปกติ (เป็น % เช่น 5 = 5%) |
| `over_salary_range_percent` | Float | **If over Salary Range %** — อัตราที่ใช้แทน เมื่อเงินเดือนเกิน Max ของ Level |
| `state` | Selection | `draft → inprocess → done` / `cancel` |
| `company_id` | M2o `res.company` | ใช้ดึง `ykk_company_working_day` ในสูตร New Salary Month |
| `line_ids` | O2m | บรรทัดคำนวณ |

**Workflow / ปุ่ม** (statusbar):
| ปุ่ม | method | เงื่อนไขแสดง | ผล |
|------|--------|-------------|-----|
| Confirm | `action_confirm` | state = draft | → inprocess |
| Done | `action_done` | state = inprocess | → done |
| Cancel | `action_cancel` | state ∈ (draft, inprocess) | → cancel |
| Reset to Draft | `action_draft` | state = cancel | → draft |
| **Excel New Salary** | `action_export_excel` | state ∈ (inprocess, done) | export .xlsx (ดู §4) |

### 2.2 Line — `ykk.kpi.salary.calculate.line`

แบ่งฟิลด์เป็น 3 กลุ่ม:

**(A) Input / default จากข้อมูลอ้างอิง**
| Field | ที่มา | แก้ในบรรทัดได้? |
|-------|-------|----------------|
| `employee_id` | เลือกเอง | ✅ |
| `level_id` | default = `employee.ykk_kpi_level_id` | ✅ (computed-editable) |
| `department_id` | default = `employee.department_id` | ✅ (computed-editable) |
| `employee_type` | **related** = `employee.ykk_kpi_employee_type` | ❌ (วิ่งตามพนักงานเสมอ) |
| `current_salary` | default = `employee.ykk_kpi_salary` | ✅ (computed-editable) |
| `grade_id` | เลือกเอง | ✅ |
| `merit` (Merit%) | default = `level.merit` (เป็น %) | ✅ (computed-editable) |
| `att` (Att%) | default = `level.att` (เป็น %) | ✅ (computed-editable) |
| `over_leave_day` | กรอกเอง | ✅ |

> **computed-editable pattern** = `compute=... , store=True, readonly=False`
> → ค่า default มาให้อัตโนมัติเมื่อ trigger เปลี่ยน แต่ user แก้ทับได้

**(B) ฟิลด์คำนวณ (read-only)**
| Field | Label | สูตร |
|-------|-------|------|
| `is_over_range` | (ซ่อน) | `current_salary > level.max_salary` (และ max_salary ต้อง > 0) |
| `effective_increase_percent` | **Increase %** | ถ้า over → `over_salary_range_percent` ไม่งั้น → `increase_percent` |
| `increase_new_salary_year` | Increase new Salary Year | `current_salary × (effective_increase_percent / 100)` |
| `plus_minus` | +/- Grade | `cal_by_grade × grade.plus_minus` |
| `cal_by_grade` | Cal By Grade | `increase_new_salary_year × (merit / 100)` |
| `cal_by_time` | Cal By Time | `increase_new_salary_year × (att / 100)` |
| `over_leave_baht` | Over Leave Baht | `(cal_by_time × over_leave_day) × (effective_increase_percent / 100)` |
| `att_amount` | Att | `cal_by_time − over_leave_baht` |
| `increase` | **Final Increase Salary** | `cal_by_grade + plus_minus + att_amount` |
| `new_salary` | New Salary | `current_salary + increase` |
| `new_salary_month` | New Salary Month | `monthly → new_salary` / `daily → new_salary × company_working_day` |

---

## 3. ตรรกะการคำนวณ (สำคัญที่สุด)

### 3.1 เงื่อนไขเลือกอัตรา (Max Salary check)
ก่อนคำนวณทุกอย่าง ระบบเช็คต่อบรรทัด:
```
ถ้า current_salary > level.max_salary  (และ level ตั้ง max_salary ไว้ > 0)
    → ใช้ over_salary_range_percent   (is_over_range = True, แสดงตัวเลขสีแดงในจอ)
ไม่งั้น
    → ใช้ increase_percent
```
ค่าที่เลือกถูกเก็บใน `effective_increase_percent` และ **ทุกสูตรที่ต้องใช้ % จะอ้างจากฟิลด์นี้** (ไม่อ้าง header ตรงๆ)
สีแดงในจอ list ใช้ `decoration-danger="is_over_range"` (มี `is_over_range` เป็น column ซ่อนใน view)

### 3.2 ลำดับการไหลของสูตร (dependency chain)
```
effective_increase_percent  ← current_salary, level.max_salary, header(increase_percent / over_salary_range_percent)
        ↓
increase_new_salary_year    ← current_salary × eff%/100
        ├─→ cal_by_grade    ← × merit/100
        │        ↓
        │   plus_minus      ← cal_by_grade × grade.plus_minus
        └─→ cal_by_time     ← × att/100
                 ↓
            over_leave_baht ← (cal_by_time × over_leave_day) × eff%/100
                 ↓
            att_amount      ← cal_by_time − over_leave_baht
                 ↓
increase (Final) = cal_by_grade + plus_minus + att_amount
        ↓
new_salary = current_salary + increase
        ↓
new_salary_month = monthly? new_salary : new_salary × company_working_day
```
ไม่มี circular dependency — Odoo จัดลำดับ recompute ให้เองจาก `@api.depends`

### 3.3 หน่วยของ %
- `increase_percent`, `over_salary_range_percent`, `merit`, `att` เก็บเป็น **ตัวเลขเปอร์เซ็นต์จริง** (เช่น 60 = 60%) → ในสูตรหารด้วย 100
- **constraint:** `merit + att ต้อง = 100` (ดู §6 Level) — ยกเว้นถ้าทั้งคู่ = 0 (level ที่ยังไม่ตั้งค่า)

### 3.4 company_working_day
- ตั้งที่ **Settings → Employees → Company Working Day** (เก็บที่ `res.company`, default 22)
- ใช้เฉพาะสูตร daily ใน `new_salary_month`

---

## 4. Excel Export (`action_export_excel`)
- ใช้ `xlsxwriter` (มากับ Odoo) สร้างไฟล์ใน memory → สร้าง `ir.attachment` → return `ir.actions.act_url` ไป `/web/content/<id>?download=true`
- คอลัมน์ = เหมือนตาราง line ทุกคอลัมน์ (19 คอลัมน์ ดู list `headers` ในโค้ด)
- ชื่อไฟล์ = เลขที่เอกสาร แทน `/` ด้วย `-` (เช่น `SC-2026-06-0001.xlsx`)
- ขยายต่อได้: เพิ่ม format ตัวเลข/ความกว้างคอลัมน์/หัวเอกสาร ที่ method นี้

---

## 5. Running Number (Sequence)
- ไฟล์ data: [`data/salary_calculate_data.xml`](data/salary_calculate_data.xml) → `ir.sequence` code `ykk.kpi.salary.calculate`
- รูปแบบ: `SC/%(year)s/%(month)s/` + padding 4 → `SC/2026/06/0001`
- `create()` override เซ็ต `name` จาก `next_by_code(...)` (pattern เดียวกับ `department_evaluate` ของ dev หลัก)
- **หมายเหตุ:** dev หลักมี `data/ir_sequence_data.xml` ที่ "ไม่ได้ใส่ใน manifest" — เราจึงแยกไฟล์ sequence ของตัวเอง ไม่ไปแตะของเขา

---

## 6. การแก้ไข/เพิ่มเติมในส่วนอื่น (เกี่ยวข้องกับ Salary Calculate)

| ส่วน | ไฟล์ | สิ่งที่ทำ |
|------|------|----------|
| **hr.employee** | [`models/hr_employee_extend.py`](models/hr_employee_extend.py) | เพิ่ม `ykk_employee_code`, `ykk_kpi_salary`, `ykk_kpi_level_id`, `ykk_kpi_group_position_id`, `ykk_kpi_employee_type`; override `_compute_display_name` → แสดง `[code] name` (global) |
| Employee form | [`views/hr_employee_extend_views.xml`](views/hr_employee_extend_views.xml) | เพิ่ม Employee Code (ก่อน Work Email) + tab **KPI Details** |
| **ykk.kpi.level** | [`models/kpi_level_extend.py`](models/kpi_level_extend.py) | เพิ่ม `merit`, `att` (%), `min_salary`, `max_salary`; constraint `max>min` และ `merit+att=100` |
| Level list | [`views/kpi_level_extend_views.xml`](views/kpi_level_extend_views.xml) | คอลัมน์: Name, Merit, Att, Min Salary, Max Salary, Description, Active |
| **ykk.kpi.grade** | [`models/kpi_grade_extend.py`](models/kpi_grade_extend.py) | เพิ่ม `plus_minus` (+/-), `grade_score` |
| Grade list | [`views/kpi_grade_extend_views.xml`](views/kpi_grade_extend_views.xml) | ย้าย Description ไปหลัง Name + เพิ่ม Grade Score, +/- |
| **res.company / settings** | [`models/res_config_settings.py`](models/res_config_settings.py), [`views/res_config_settings_views.xml`](views/res_config_settings_views.xml) | เพิ่ม **Company Working Day** ใน Settings ของแอป Employees |
| (ลบออก) Increase Salary Setting | — | เมนู/model `ykk.kpi.increase.salary.setting` ถูกลบ และย้าย Min/Max Salary ไปไว้ที่ Level |

ความสัมพันธ์ของฟิลด์ที่ Salary Calculate ดึงไปใช้:
```
hr.employee.ykk_kpi_level_id      → line.level_id      → level.merit / level.att / level.max_salary
hr.employee.ykk_kpi_salary        → line.current_salary
hr.employee.ykk_kpi_employee_type → line.employee_type (related)
hr.employee.department_id         → line.department_id
ykk.kpi.grade.plus_minus          → line.plus_minus
ykk.kpi.grade.grade_score         → (ปัจจุบันยังไม่ถูกใช้ในสูตร line — เผื่อพัฒนาต่อ)
res.company.ykk_company_working_day → line.new_salary_month (daily)
```

---

## 7. ไฟล์ที่เกี่ยวข้อง (file map)
```
ykk_kpi_management/
├── data/salary_calculate_data.xml          # ir.sequence
├── models/
│   ├── salary_calculate.py                 # header + line + สูตรทั้งหมด + excel
│   ├── hr_employee_extend.py               # employee fields + display_name
│   ├── kpi_level_extend.py                 # merit/att/min/max + constraints
│   ├── kpi_grade_extend.py                 # plus_minus / grade_score
│   └── res_config_settings.py              # company_working_day
├── views/
│   ├── salary_calculate_views.xml          # form/list/search/menu/ปุ่ม
│   ├── hr_employee_extend_views.xml
│   ├── kpi_level_extend_views.xml
│   ├── kpi_grade_extend_views.xml
│   └── res_config_settings_views.xml
└── security/ir.model.access.csv            # access ของ salary.calculate (+ line)
```
ทุกไฟล์ลงทะเบียนแล้วใน `models/__init__.py` และ `__manifest__.py`

---

## 8. ข้อควรระวังสำหรับการพัฒนาต่อ (gotchas)

1. **ฟิลด์คำนวณเป็น `store=True`** — ถ้าแก้สูตรใน method แต่ "ไม่ได้เพิ่ม/ลบฟิลด์" Odoo **จะไม่ recompute ข้อมูลเก่าอัตโนมัติ** ตอน `-u`
   ต้อง recompute เองผ่าน odoo shell เช่น:
   ```python
   recs = env['ykk.kpi.salary.calculate.line'].search([])
   recs._compute_increase()        # เรียก compute ที่เกี่ยว
   env.flush_all(); env.cr.commit()
   ```
2. **ถ้าลบฟิลด์ที่ inherited view อ้างถึง** จะเจอ ParseError ตอน upgrade (stale view ใน DB) — ลบ view record ที่ค้างก่อน แล้ว upgrade ใหม่
3. `employee_type` เป็น **related (readonly)** — ถ้าต้องการให้แก้รายบรรทัดได้ ต้องเปลี่ยนกลับเป็น computed-editable
4. `_compute_display_name` ของ hr.employee เป็น **global** (มีผลทุกหน้าจอที่แสดงพนักงาน) — ถ้าไม่ต้องการ global ต้องเปลี่ยน approach
5. การ "เกิน Max Salary" จะข้ามถ้า `level.max_salary = 0` (ถือว่าไม่ได้ตั้งค่า) — ระวังตอนตั้ง business rule
6. หน่วย % ทั้งหมดเป็นตัวเลขจริง (หาร 100 ในสูตร) — ห้ามใส่ widget `percentage` เพราะจะหาร 100 ซ้ำ

---

## 9. วิธี deploy / ทดสอบ
```bash
# upgrade module
docker compose exec odoo odoo -u ykk_kpi_management -d <db> --stop-after-init
docker compose restart odoo
```
ทดสอบ: ตั้ง Max Salary/merit/att ที่ Level → ตั้งเงินเดือน/level/type ที่พนักงาน → สร้างเอกสาร Salary Calculate → กรอก Increase new % / If over Salary Range % → เพิ่มบรรทัดเลือกพนักงาน+grade → ตรวจค่าคำนวณ → Confirm → กด Excel New Salary
