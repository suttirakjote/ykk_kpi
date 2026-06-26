/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component, useState, useRef, onWillStart } from "@odoo/owl";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { useService } from "@web/core/utils/hooks";

const GRADES = ["A", "B", "C", "D", "E"];

/**
 * Drag-and-drop board, grouped by department.
 *  - The lines are grouped by department. Each department renders:
 *      * a summary block on the LEFT (department merged into one cell that
 *        spans all its employees), and
 *      * its own row of grade columns A-E on the RIGHT.
 *  - Each employee card sits in the grade column equal to its new_grade,
 *    within its own department's board.
 *  - Dragging a card to another column (in the same department) sets new_grade.
 *  - A card whose new_grade != current_grade is shown red (moved).
 *  - Hide Summary collapses every summary column except Department.
 *  - Full Screen expands the whole board to the viewport.
 */
export class KpiGradeBoardField extends Component {
    static template = "ykk_kpi_management.GradeBoard";
    static props = { ...standardFieldProps };

    setup() {
        this.root = useRef("root");
        this.orm = useService("orm");
        this.state = useState({
            draggingId: null,
            dragOverKey: null, // `${deptId}:${grade}` of the column hovered
            showSummary: true,
            fullscreen: false,
        });
        // โหลด Relative Adjustment Group (คอลัมน์) + Grade (adjustment_score) มาคำนวณตารางสรุป
        this.adjState = useState({ groups: [], gradeById: {}, adjScoreByName: {} });
        onWillStart(async () => {
            const [groups, grades] = await Promise.all([
                this.orm.searchRead(
                    "ykk.kpi.relative.adjustment.group",
                    [],
                    ["name", "board_label", "grade_ids", "distribution", "sequence"],
                    { order: "sequence, id" }
                ),
                this.orm.searchRead("ykk.kpi.grade", [], ["name", "adjustment_score"]),
            ]);
            const gradeById = {};
            const adjScoreByName = {};
            for (const g of grades) {
                gradeById[g.id] = g;
                adjScoreByName[g.name] = g.adjustment_score || 0;
            }
            this.adjState.groups = groups;
            this.adjState.gradeById = gradeById;
            this.adjState.adjScoreByName = adjScoreByName;
        });
        this._onFsChange = () => {
            const active = !!document.fullscreenElement;
            if (!active && this.state.fullscreen) {
                this.state.fullscreen = false;
            }
        };
        document.addEventListener("fullscreenchange", this._onFsChange);
    }

    get grades() {
        return GRADES;
    }

    // ----- SUMMARY MATRIX (3 color groups x 3 metrics) -----
    get summaryGroups() {
        return [
            { key: "white", className: "o_kpi_sum_white" },
            { key: "blue", className: "o_kpi_sum_blue" },
            { key: "red", className: "o_kpi_sum_red" },
        ];
    }

    get summaryMetrics() {
        return ["Number of people", "Distribution", "Average"];
    }

    // คอลัมน์ของตารางสรุป = Relative Adjustment Group
    get adjustmentGroups() {
        return this.adjState.groups;
    }

    // ----- helpers สำหรับสูตรคำนวณ (live ตาม new_grade ที่ลากบน board) -----
    get total() {
        // จำนวนพนักงานทั้งหมดของทุกเกรด
        return this.lines.length;
    }

    gradeCount(gradeName) {
        // จำนวนคนของเกรดนั้น (อิงตาม New Grade)
        return this.lines.filter((l) => l.data.new_grade === gradeName).length;
    }

    groupGradeNames(grp) {
        const byId = this.adjState.gradeById;
        return (grp.grade_ids || [])
            .map((id) => byId[id] && byId[id].name)
            .filter(Boolean);
    }

    _whiteNum(grp) {
        // Sum จำนวนพนักงานทั้งหมดของเกรดที่อยู่ใน group นี้
        return this.groupGradeNames(grp).reduce((s, n) => s + this.gradeCount(n), 0);
    }

    _blueNum(grp) {
        // Distribution(blue) * total
        return ((grp.distribution || 0) / 100) * this.total;
    }

    get _averageScore() {
        // Σ(จำนวนคนของเกรด × Adjustment Score ของเกรด) / total  (ทุกเกรด A-E)
        const total = this.total;
        if (!total) {
            return 0;
        }
        let sum = 0;
        for (const [name, score] of Object.entries(this.adjState.adjScoreByName)) {
            sum += this.gradeCount(name) * score;
        }
        return sum / total;
    }

    _round(v) {
        return Math.round((v + Number.EPSILON) * 100) / 100;
    }

    /**
     * Value for a summary cell.
     * @param groupKey color group (white/blue/red)
     * @param metric   Number of people / Distribution / Average
     * @param grp      the Relative Adjustment Group record
     */
    summaryValue(groupKey, metric, grp) {
        const total = this.total;
        const whiteNum = this._whiteNum(grp);
        const whiteDist = total ? (whiteNum / total) * 100 : 0;
        const blueDist = grp.distribution || 0;
        const blueNum = this._blueNum(grp);
        const avg = this._averageScore;

        if (groupKey === "white") {
            if (metric === "Number of people") return whiteNum;
            if (metric === "Distribution") return this._round(whiteDist) + "%";
            if (metric === "Average") return this._round(avg);
        } else if (groupKey === "blue") {
            if (metric === "Number of people") return this._round(blueNum);
            if (metric === "Distribution") return this._round(blueDist) + "%";
            if (metric === "Average") return this._round(avg);
        } else if (groupKey === "red") {
            if (metric === "Number of people") return this._round(whiteNum - blueNum);
            if (metric === "Distribution") return this._round(whiteDist - blueDist) + "%";
            if (metric === "Average") return this._round(avg - avg);
        }
        return "";
    }

    get lines() {
        return this.props.record.data[this.props.name].records;
    }

    /**
     * Group lines by department, preserving first-seen order.
     * Returns: [{ id, name, lines: [...] }, ...]
     */
    get departments() {
        const groups = [];
        const byId = {};
        for (const line of this.lines) {
            const dep = line.data.department_id;
            const depId = dep ? dep[0] : 0;
            const depName = dep ? dep[1] : "No Department";
            if (!byId[depId]) {
                byId[depId] = { id: depId, name: depName, lines: [] };
                groups.push(byId[depId]);
            }
            byId[depId].lines.push(line);
        }
        return groups;
    }

    linesForGradeIn(deptLines, grade) {
        return deptLines.filter((l) => l.data.new_grade === grade);
    }

    isMoved(line) {
        return line.data.new_grade !== line.data.current_grade;
    }

    colKey(deptId, grade) {
        return `${deptId}:${grade}`;
    }

    get readonly() {
        return this.props.readonly;
    }

    // ---- UI toggles ----
    toggleSummary() {
        this.state.showSummary = !this.state.showSummary;
    }

    async toggleFullscreen() {
        const el = this.root.el;
        if (!document.fullscreenElement) {
            if (el && el.requestFullscreen) {
                await el.requestFullscreen();
            }
            this.state.fullscreen = true;
        } else {
            if (document.exitFullscreen) {
                await document.exitFullscreen();
            }
            this.state.fullscreen = false;
        }
    }

    // ---- drag handlers ----
    onDragStart(ev, line) {
        if (this.readonly) {
            ev.preventDefault();
            return;
        }
        this.state.draggingId = line.id;
        ev.dataTransfer.effectAllowed = "move";
        ev.dataTransfer.setData("text/plain", String(line.id));
    }

    onDragOver(ev, deptId, grade) {
        if (this.readonly || this.state.draggingId === null) {
            return;
        }
        ev.preventDefault();
        ev.dataTransfer.dropEffect = "move";
        this.state.dragOverKey = this.colKey(deptId, grade);
    }

    onDragLeave(deptId, grade) {
        if (this.state.dragOverKey === this.colKey(deptId, grade)) {
            this.state.dragOverKey = null;
        }
    }

    async onDrop(ev, deptId, grade) {
        ev.preventDefault();
        const draggingId = this.state.draggingId;
        this.state.draggingId = null;
        this.state.dragOverKey = null;
        if (draggingId === null) {
            return;
        }
        const line = this.lines.find((l) => l.id === draggingId);
        if (!line) {
            return;
        }
        // Only allow dropping within the same department.
        const lineDeptId = line.data.department_id
            ? line.data.department_id[0]
            : 0;
        if (lineDeptId !== deptId) {
            return;
        }
        if (line.data.new_grade !== grade) {
            await line.update({ new_grade: grade });
        }
    }

    onDragEnd() {
        this.state.draggingId = null;
        this.state.dragOverKey = null;
    }
}

registry.category("fields").add("kpi_grade_board", {
    component: KpiGradeBoardField,
    supportedTypes: ["one2many"],
    relatedFields: [
        { name: "employee_id", type: "many2one" },
        { name: "department_id", type: "many2one" },
        { name: "current_grade", type: "selection", selection: GRADES.map((g) => [g, g]) },
        { name: "new_grade", type: "selection", selection: GRADES.map((g) => [g, g]) },
    ],
});
