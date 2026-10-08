import base64
import io

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


ATTITUDE_COLUMNS = {
    "tardiness": "Tardiness",
    "unexplained_absence": "Unexplained Absence",
    "verbal_reprimand": "Verbal Reprimand",
    "warning_letter": "Warning Letter",
    "suspension": "Suspension",
}

HEADER_MAP = {
    "year": "year",
    "employee code": "employee_code",
    **{label.lower(): key for key, label in ATTITUDE_COLUMNS.items()},
}


class ImportAttitude(models.Model):
    _name = "ykk.kpi.import.attitude"
    _description = "Import Attitude"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "id desc"

    name = fields.Char(
        string="Reference",
        default="New",
        readonly=True,
        copy=False,
    )
    date = fields.Date(
        string="Date",
        default=fields.Date.context_today,
        required=True,
        tracking=True,
    )
    period_id = fields.Many2one(
        "ykk.kpi.period",
        string="Period",
        tracking=True,
    )
    user_id = fields.Many2one(
        "res.users",
        string="Uploaded By",
        default=lambda self: self.env.user,
        readonly=True,
    )
    upload_file = fields.Binary(string="Upload", attachment=True)
    upload_filename = fields.Char(string="File Name")
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("inprocess", "In Process"),
            ("confirm", "Confirm"),
        ],
        string="Status",
        default="draft",
        required=True,
        copy=False,
        tracking=True,
    )
    line_ids = fields.One2many(
        "ykk.kpi.import.attitude.line",
        "import_id",
        string="Data",
        copy=False,
    )
    company_id = fields.Many2one(
        "res.company",
        string="Company",
        required=True,
        default=lambda self: self.env.company,
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", "New") == "New":
                vals["name"] = (
                    self.env["ir.sequence"].next_by_code(
                        "ykk.kpi.import.attitude"
                    )
                    or "New"
                )
        return super().create(vals_list)

    @staticmethod
    def _normalize_employee_code(value):
        if value in (None, ""):
            return ""
        if isinstance(value, float) and value.is_integer():
            return str(int(value))
        return str(value).strip()

    @staticmethod
    def _frequency_value(value, row_number, column_label):
        if value in (None, ""):
            return 0
        try:
            number = float(value)
        except (TypeError, ValueError):
            raise ValidationError(
                _(
                    "Row %(row)s: %(column)s must be a number.",
                    row=row_number,
                    column=column_label,
                )
            )
        if number < 0 or not number.is_integer():
            raise ValidationError(
                _(
                    "Row %(row)s: %(column)s must be a non-negative whole number.",
                    row=row_number,
                    column=column_label,
                )
            )
        return int(number)

    @staticmethod
    def _get_attitude_line_code(attitude_line):
        """Return the stored code, or extract it from legacy '[CODE] Name' data."""
        if attitude_line.hr_evaluation_code:
            return attitude_line.hr_evaluation_code.strip()
        name = (attitude_line.name or "").strip()
        if name.startswith("[") and "]" in name:
            return name[1:name.index("]")].strip()
        return ""

    def _parse_rows(self):
        self.ensure_one()
        if not self.upload_file:
            return []

        try:
            import openpyxl

            workbook = openpyxl.load_workbook(
                io.BytesIO(base64.b64decode(self.upload_file)),
                data_only=True,
            )
        except Exception as error:
            raise ValidationError(_("Unable to read the Excel file: %s") % error)

        sheet = workbook.active
        rows = list(sheet.iter_rows(values_only=True))
        if not rows:
            return []

        headers = [
            str(header).strip().lower() if header is not None else ""
            for header in rows[0]
        ]
        columns = {
            HEADER_MAP[header]: index
            for index, header in enumerate(headers)
            if header in HEADER_MAP
        }
        required_columns = {"year", "employee_code", *ATTITUDE_COLUMNS}
        missing_columns = required_columns - set(columns)
        if missing_columns:
            labels = {
                "year": "Year",
                "employee_code": "Employee Code",
                **ATTITUDE_COLUMNS,
            }
            raise ValidationError(
                _("Missing required column(s): %s")
                % ", ".join(labels[column] for column in sorted(missing_columns))
            )

        def cell(row, field_name):
            index = columns[field_name]
            return row[index] if index < len(row) else None

        parsed_rows = []
        for row_number, row in enumerate(rows[1:], start=2):
            if not row or all(value is None for value in row):
                continue
            year_value = cell(row, "year")
            try:
                year_number = float(year_value)
                if not year_number.is_integer() or year_number <= 0:
                    raise ValueError
                year = int(year_number)
            except (TypeError, ValueError):
                raise ValidationError(
                    _("Row %s: Year must be a positive whole number.")
                    % row_number
                )

            values = {
                "year": year,
                "employee_code": self._normalize_employee_code(
                    cell(row, "employee_code")
                ),
            }
            for attitude_type, label in ATTITUDE_COLUMNS.items():
                values[attitude_type] = self._frequency_value(
                    cell(row, attitude_type),
                    row_number,
                    label,
                )
            parsed_rows.append(values)
        return parsed_rows

    def _build_line_commands(self):
        self.ensure_one()
        employee_model = self.env["hr.employee"]
        commands = [(5, 0, 0)]
        for values in self._parse_rows():
            employee = employee_model.search(
                [("ykk_employee_code", "=", values["employee_code"])],
                limit=1,
            )
            commands.append((0, 0, {
                **values,
                "employee_id": employee.id if employee else False,
            }))
        return commands

    @api.onchange("upload_file")
    def _onchange_upload_file(self):
        for record in self:
            record.line_ids = (
                record._build_line_commands()
                if record.upload_file
                else [(5, 0, 0)]
            )

    def _ensure_import_lines(self):
        self.ensure_one()
        if not self.period_id:
            raise ValidationError(_("Please select a Period."))
        if not self.upload_file:
            raise ValidationError(_("Please upload an Excel file."))
        if not self.line_ids:
            self.write({"line_ids": self._build_line_commands()})
        if not self.line_ids:
            raise ValidationError(_("The uploaded file does not contain any data."))

    def action_inprocess(self):
        self.ensure_one()
        if not self.period_id:
            raise ValidationError(_("Please select a Period."))
        if not self.upload_file:
            raise ValidationError(_("Please upload an Excel file."))
        self.write({
            "line_ids": self._build_line_commands(),
            "state": "inprocess",
        })
        if not self.line_ids:
            raise ValidationError(_("The uploaded file does not contain any data."))

    def action_confirm(self):
        self.ensure_one()
        self._ensure_import_lines()

        employee_model = self.env["hr.employee"]
        evaluation_model = self.env["ykk.kpi.department.kpi"]
        attitude_model = self.env["ykk.kpi.hr.evaluation"]
        configurations = attitude_model.search([
            ("type", "=", "attitude"),
            ("attitude_type", "!=", False),
            ("company_id", "=", self.company_id.id),
            ("active", "=", True),
        ])
        configurations_by_type = {
            attitude_type: configurations.filtered(
                lambda configuration, key=attitude_type:
                    configuration.attitude_type == key
            )
            for attitude_type in ATTITUDE_COLUMNS
        }
        missing_configuration = [
            label
            for attitude_type, label in ATTITUDE_COLUMNS.items()
            if not configurations_by_type[attitude_type]
        ]
        if missing_configuration:
            raise ValidationError(
                _("Please configure HR Evaluation for Attitude Type: %s")
                % ", ".join(missing_configuration)
            )

        operations = []
        errors = []
        updated_evaluations = self.env["ykk.kpi.department.kpi"]
        for line in self.line_ids:
            employee = employee_model.search(
                [("ykk_employee_code", "=", line.employee_code)],
                limit=1,
            )
            if not employee:
                errors.append(
                    _("Employee Code %(code)s was not found.", code=line.employee_code)
                )
                continue

            evaluations = evaluation_model.search([
                ("employee_id", "=", employee.id),
                ("company_id", "=", self.company_id.id),
                ("period_id", "=", self.period_id.id),
            ])
            if not evaluations:
                errors.append(
                    _(
                        "Evaluation was not found for Employee Code %(code)s "
                        "in Period %(period)s.",
                        code=line.employee_code,
                        period=self.period_id.name,
                    )
                )
                continue

            for evaluation in evaluations:
                for attitude_type, label in ATTITUDE_COLUMNS.items():
                    configs = configurations_by_type[attitude_type]
                    config_codes = {
                        code.strip()
                        for code in configs.mapped("code")
                        if code
                    }
                    target_lines = evaluation.attitude_line_ids.filtered(
                        lambda attitude_line: self._get_attitude_line_code(
                            attitude_line
                        ) in config_codes
                    )
                    if not target_lines:
                        errors.append(
                            _(
                                "Attitude line %(type)s was not found in Evaluation "
                                "%(evaluation)s.",
                                type=label,
                                evaluation=evaluation.display_name,
                            )
                        )
                        continue
                    operations.append((target_lines, line[attitude_type]))
                updated_evaluations |= evaluation

        if errors:
            raise ValidationError("\n".join(dict.fromkeys(errors)))

        updated_line_count = 0
        for target_lines, frequency in operations:
            target_lines.write({"frequency": frequency})
            updated_line_count += len(target_lines)

        self.write({"state": "confirm"})
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Import Attitude Completed"),
                "message": _(
                    "Updated %(evaluations)s Evaluation document(s) and "
                    "%(lines)s Attitude line(s).",
                    evaluations=len(updated_evaluations),
                    lines=updated_line_count,
                ),
                "type": "success",
                "sticky": False,
                "next": {
                    "type": "ir.actions.client",
                    "tag": "soft_reload",
                },
            },
        }


class ImportAttitudeLine(models.Model):
    _name = "ykk.kpi.import.attitude.line"
    _description = "Import Attitude Line"
    _order = "id"

    import_id = fields.Many2one(
        "ykk.kpi.import.attitude",
        required=True,
        ondelete="cascade",
    )
    year = fields.Integer(string="Year", required=True)
    employee_code = fields.Char(string="Employee Code", required=True)
    employee_id = fields.Many2one("hr.employee", string="Employee", readonly=True)
    tardiness = fields.Integer(string="Tardiness")
    unexplained_absence = fields.Integer(string="Unexplained Absence")
    verbal_reprimand = fields.Integer(string="Verbal Reprimand")
    warning_letter = fields.Integer(string="Warning Letter")
    suspension = fields.Integer(string="Suspension")
