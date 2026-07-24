# คู่มือการใช้งานเบื้องต้น — ระบบ KPI Management (YKK)

เอกสารนี้สำหรับผู้ใช้ทดสอบระบบ อธิบายการใช้งานของทุกเมนูในแอป **KPI Management**

---

## 1. ภาพรวมระบบ

ระบบ KPI Management ใช้สำหรับ ตั้งค่า KPI → ประเมินผล → ปรับเกรด → คำนวณการขึ้นเงินเดือน/โบนัส

**เข้าระบบ:** เปิดเบราว์เซอร์ → URL ของระบบ → เลือกแอป **KPI Management** บนแถบเมนูด้านบน

**แถบเมนูหลัก:** `Evaluate` · `Adjustment` · `Calculate` · `Configuration`

> 💡 ครั้งแรกควรตั้งค่าที่เมนู **Configuration** ให้ครบก่อน แล้วจึงเริ่มใช้งานเมนูอื่น

---

## 2. ลำดับการใช้งานที่แนะนำ

```
(1) Configuration : ตั้งค่าข้อมูลพื้นฐาน (Period, Level, Grade, Goal, Template, พนักงาน ฯลฯ)
        ↓
(2) Evaluate      : ทำเอกสารประเมิน (Annual KPI → Department KPI)
        ↓
(3) Adjustment    : ปรับเกรดพนักงาน (ดึงผลจาก Department KPI)
        ↓
(4) Calculate     : คำนวณเงินเดือน/โบนัส (ดึงเกรดที่ปรับแล้ว)
```

---

## 3. เมนู Configuration (ตั้งค่าก่อนใช้งาน)

### 3.1 Periods (รอบประเมิน)
กำหนดรอบการประเมิน
- **Name** : ชื่อรอบ เช่น "รอบประเมินครั้งที่ 1"
- **Period Type** : Month / Quarter / Half Year / Year
- **Start Date / End Date** : ช่วงวันที่ (เริ่มต้องไม่เกินสิ้นสุด)

### 3.2 Job Levels (ระดับตำแหน่ง)
- **Name** : ชื่อระดับ เช่น SS1, SA5
- **Merit %** และ **Att %** : ค่าเป็นเปอร์เซ็นต์ — **สองช่องนี้รวมกันต้องได้ 100%**
- **Min Salary / Max Salary** : ช่วงเงินเดือนของระดับ (Max ต้องมากกว่า Min)

### 3.3 Group Positions (กลุ่มตำแหน่งงาน)
- **Name** : ชื่อกลุ่ม เช่น Admin, Operation

### 3.4 Grades (เกรด)
- **Code** : รหัสเกรด (ใช้จับคู่คะแนน เช่น 5=A, 1=E)
- **Name** : ชื่อเกรด A–E
- **Start Score / End Score** : ช่วงคะแนนของเกรด
- **Grade Score** : คะแนนเกรด (ใช้ในสูตร Salary Calculate)
- **Adjustment Score** : คะแนนปรับ (ใช้ในตารางสรุป Grade Board)
- **+/-** : ค่าปรับของเกรด

### 3.5 Goals (เป้าหมาย/ตัวชี้วัด)
ตัวชี้วัดที่นำไปใช้ใน Template และการประเมิน
- **Code / Name** : รหัส/ชื่อ (ไม่ซ้ำต่อบริษัท)
- **Type** : Performance / Role-based Behavior / Behavior / Attitude
- **Department** : แผนกที่เกี่ยวข้อง

### 3.6 HR Evaluations (หัวข้อประเมินด้านพฤติกรรม)
หัวข้อสำหรับ tab Role-based / Behavior / Attitude
- **Code / Name / Group Type / Type / Department**

### 3.7 Template KPI (เทมเพลต KPI)
แม่แบบเกณฑ์ประเมินตามระดับ/แผนก (เลขรันอัตโนมัติ KT/ปี/เดือน/xxxx)
- **Header** : Level, Department, Remark, Status (Draft/Done/Cancel)
- **Tab Performance Evaluation** : Goal, Achievement Criteria, Weight
- **Tab Employees** : พนักงานที่ใช้เทมเพลตนี้ (กรองตาม Department + Level)
- กด**ทำให้เป็น Done** เพื่อให้พร้อมใช้งานใน Annual KPI

### 3.8 Relative Adjustment Group (กลุ่มการปรับเทียบ)
ใช้ในตารางสรุปของ Grade Board
- **ลำดับ** : ลากจุดหน้าแถวเพื่อจัดเรียง (sequence)
- **Name** : ชื่อกลุ่ม เช่น Group1
- **Grade** : เลือกได้หลายเกรด (เช่น A, B) — แสดงเป็น "Group1(A,B)"
- **Distribution (%)** : เป้าหมายการกระจาย % (ส่วนสีน้ำเงินในตารางสรุป)

### 3.9 Employees (พนักงาน)
ข้อมูลพนักงาน — ในฟอร์มมี **Employee Code** (เหนือ Work Email) และแท็บ **KPI Details**:
- **Salary** : เงินเดือนปัจจุบัน
- **Job Level** : ระดับ (จาก Job Levels)
- **Group Position** : กลุ่มตำแหน่ง
- **Employee Type** : Monthly / Daily

> ⚙️ **ตั้งค่าเพิ่ม:** ไปที่ **Settings → Employees → Company Working Day** กำหนดจำนวนวันทำงานต่อเดือน (ใช้คำนวณ New Salary Month ของพนักงาน Daily, ค่าเริ่มต้น 22)

### 3.10 Departments / Job Positions
ลิงก์ไปหน้าจอมาตรฐานของ Odoo (จัดการแผนก/ตำแหน่งงาน)

---

## 4. เมนู Evaluate (การประเมิน)

### 4.1 Annual KPI (KPI ประจำปี)
ตั้ง KPI รายบุคคลต่อรอบ (เลขรัน AN/ปี/เดือน/xxxx)
1. กด **New** → เลือก **Employee** (ระบบดึง Department + เทมเพลตให้อัตโนมัติ)
2. เลือก **Period**, ตรวจ Group Job / Job Level
3. ตรวจ/แก้ tab:
   - **Performance Evaluation** : มาจาก Template KPI
   - **Role-based / Behavior / Attitude** : มาจาก HR Evaluations
4. ใส่ค่าน้ำหนัก (weights) ใน Other Info
5. กด **Confirm → Done** ตามสถานะ

### 4.2 Department KPI (ประเมินผลจริง)
บันทึกผลคะแนนจริง (เลขรัน DE/ปี/เดือน/xxxx)
1. กด **New** → เลือก Employee, Period
2. เลือก **Annual KPI** ที่เกี่ยวข้อง แล้วกดปุ่ม **update** (ข้าง Annual KPI) → ระบบดึงหัวข้อจาก Annual KPI มาลงทุก tab (ยกเว้น Summary)
3. กรอกคะแนนในแต่ละ tab: Performance / Role-based / Behavior / Attitude
   - ใส่ Score (First/Second Evaluator), ระบบคำนวณ **Total** ให้
4. **Tab Summary** :
   - **Period Grade** / **Overall Grade** : ระบบคำนวณเกรดให้
   - **Adjust Grade** : เกรดหลังปรับ (มาจากหน้า Adjustment)
   - **Parent KPIs** : เพิ่ม KPI แม่เพื่อเฉลี่ยเป็น Overall Grade
5. Workflow: **Confirm** (→ Inprocess) → **Done** (→ Evaluated) / **Cancel**

> ⚠️ เอกสารที่จะนำไปปรับเกรด/คำนวณต่อได้ **ต้องเป็นสถานะ Evaluated เท่านั้น**

---

## 5. เมนู Adjustment (การปรับเกรด)

### 5.1 Adjustments (KPI Grade Adjustments)
ปรับเกรดพนักงานเป็นกลุ่ม (เลขรัน KPI/ปี/xxxx)
1. กด **New** → เลือก **KPI Period** และ **Job Level**
2. กด **Load Employees** → ระบบดึงพนักงานจาก Department KPI ที่
   - Period ตรงกัน + Job Level ตรงกัน + สถานะ **Evaluated**
   - **Current Grade** = Overall Grade ของเอกสารนั้น (อ้างใน **Document Ref**)
3. ปรับ **New Grade** ได้ 3 มุมมอง (แท็บ):
   - **Grade Lines** : ตารางแก้ค่าโดยตรง (แถวที่เปลี่ยนเกรดจะเป็นสีแดง)
   - **Grade Grid** : ตารางช่อง A–E คลิกช่องเพื่อเลือกเกรด
   - **Grade Board** : ลากการ์ดพนักงานข้ามคอลัมน์เกรด + มีตารางสรุป 3 สี (ขาว=ปัจจุบัน / น้ำเงิน=เป้าหมาย / แดง=ส่วนต่าง) แยกตาม Relative Adjustment Group
4. กด **Confirm** → ระบบบันทึกประวัติ + อัปเดตเกรดใหม่กลับไปที่พนักงาน
5. ปุ่ม **Department KPI** (มุมขวาบน) = ลิงก์ดูเอกสารต้นทาง

### 5.2 Grade History (ประวัติการปรับเกรด)
ดูประวัติการเปลี่ยนเกรดทั้งหมด (อ่านอย่างเดียว) — Employee, Period, Old Grade, New Grade, ผู้แก้ไข

---

## 6. เมนู Calculate (คำนวณ)

### 6.1 Salary Calculate (คำนวณขึ้นเงินเดือน)
เลขรัน SC/ปี/เดือน/xxxx
1. กด **New** → เลือก **Period**, ใส่ **Increase new %** และ **If over Salary Range %**
2. กด **Load Employee** → ดึงพนักงานจาก Department KPI (Evaluated, Period ตรง) โดย **Grade = Adjust Grade** ที่ปรับไว้
3. ระบบคำนวณให้อัตโนมัติต่อบรรทัด เช่น Increase new Salary Year, Cal By Grade/Time, New Salary, New Salary Month
   - คอลัมน์ **Increase %** : ถ้าเงินเดือนเกิน Max ของ Level จะใช้ "If over Salary Range %" และแสดงเป็น**สีแดง**
4. Workflow: **Confirm → Done** / **Cancel**
5. ปุ่ม **Excel New Salary** (สถานะ In Process/Done) → ดาวน์โหลดผลเป็นไฟล์ Excel (ชื่อไฟล์ = เลขเอกสาร)

### 6.2 Bonus Calculate (คำนวณโบนัส)
เลขรัน BN/ปี/เดือน/xxxx
1. กด **New** → เลือก **Period**, ใส่ **Bonus (Month)** และ **Work Day of Year**
2. กด **Load Employee** → ดึงพนักงานจาก Department KPI (Evaluated, Period ตรง), Grade = Adjust Grade
3. กรอกค่าที่ต้องใส่เอง: **COLA, POST, Serv.Year, Minus Leave/Day**
   - **Day ATT** ดึงค่าจาก Work Day of Year (แก้รายบรรทัดได้)
   - ระบบคำนวณ Serv.Year Amount, Bonus, Bonus(GRD), Bonus-Leave, **Net Pay** ให้
4. Workflow: **Confirm → Done** / **Cancel**
5. ปุ่ม **Excel Bonus** (สถานะ In Process/Done) → ดาวน์โหลดผลเป็น Excel

---

## 7. สรุปขั้นตอนทดสอบแบบ End-to-End

1. **Configuration** : สร้าง Period, Job Level (Merit+Att=100), Group Position, Grade (ใส่ Grade Score/Adjustment Score/Code), Goal, HR Evaluation, Template KPI (Done), Relative Adjustment Group, ตั้งค่าพนักงาน (KPI Details) + Company Working Day
2. **Annual KPI** : สร้างต่อพนักงาน → Done
3. **Department KPI** : สร้าง → กด update ดึงจาก Annual → กรอกคะแนน → Confirm → Done (Evaluated)
4. **Adjustments** : เลือก Period+Job Level → Load Employees → ปรับ New Grade → Confirm
5. **Salary Calculate / Bonus Calculate** : เลือก Period → Load Employee → ตรวจผล → Confirm → Done → Export Excel

---

## 8. ปุ่ม/ไอคอนที่พบบ่อย

| ปุ่ม/ไอคอน | ความหมาย |
|-----------|----------|
| **New** | สร้างเอกสารใหม่ |
| **Confirm / Done / Cancel** | เปลี่ยนสถานะเอกสาร (workflow) |
| **Load Employees / Load Employee** | ดึงรายชื่อพนักงานเข้าเอกสารอัตโนมัติ |
| ไอคอน ⚙️ (sliders) มุมขวาหัวตาราง | เปิด/ปิดการแสดงคอลัมน์ |
| Status bar (มุมขวาบน) | สถานะปัจจุบันของเอกสาร |

---

หากพบปัญหาระหว่างทดสอบ กรุณาแจ้งทีมพัฒนา พร้อมระบุเมนู/เลขที่เอกสาร และขั้นตอนที่ทำ
