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
    static template = "ykk_kpi_management.GradeGrid";
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

registry.category("fields").add("kpi_grade_grid", {
    component: KpiGradeGridField,
    supportedTypes: ["one2many"],
    relatedFields: [
        { name: "employee_id", type: "many2one" },
        { name: "department_id", type: "many2one" },
        { name: "current_grade", type: "selection", selection: GRADES.map((g) => [g, g]) },
        { name: "new_grade", type: "selection", selection: GRADES.map((g) => [g, g]) },
    ],
});
