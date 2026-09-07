/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component } from "@odoo/owl";
import { standardFieldProps } from "@web/views/fields/standard_field_props";

const GRADES = ["A", "B", "C", "D", "E"];

/**
 * Renders the adjustment lines as a spreadsheet-like grid.
 * Each row = one employee. Columns A-E. The cell matching new_grade is
 * filled; green when new_grade == current_grade, red when changed.
 * Clicking a cell sets new_grade for that line.
 */
export class KpiGradeGridField extends Component {
    static template = "ykk_kpi.GradeGrid";
    static props = { ...standardFieldProps };

    get grades() {
        return GRADES;
    }

    get lines() {
        // The x2many "list" record exposes records via .records
        return this.props.record.data[this.props.name].records;
    }

    get groupedLines() {
        const groups = {};
        for (const line of this.lines) {
            const dep = line.data.department_id
                ? line.data.department_id[1]
                : "No Department";
            (groups[dep] = groups[dep] || []).push(line);
        }
        return Object.entries(groups).map(([name, lines]) => ({ name, lines }));
    }

    cellState(line, grade) {
        const isSelected = line.data.new_grade === grade;
        if (!isSelected) {
            return "empty";
        }
        const changed = line.data.new_grade !== line.data.current_grade;
        return changed ? "changed" : "matched"; // red : green
    }

    get readonly() {
        return this.props.readonly;
    }

    async onCellClick(line, grade) {
        if (this.readonly) {
            return;
        }
        await line.update({ new_grade: grade });
    }
}

// หมายเหตุ: ห้ามใช้ relatedFields ที่นี่
// ฟอร์มนี้วาง line_ids ไว้ 3 ที่ (list ปกติ + grid + board) Odoo จะ merge
// field description ของทั้ง 3 เข้าด้วยกัน โดย relatedFields เป็น object ที่ไม่มี
// key "string" จึงไปทับ label ของฟิลด์จริง ทำให้หัวตารางในแท็บ Grade Lines หายไป
// จึงประกาศฟิลด์ที่ widget ต้องใช้เป็น inline <list> ในไฟล์ view แทน
registry.category("fields").add("kpi_grade_grid", {
    component: KpiGradeGridField,
    supportedTypes: ["one2many"],
});
