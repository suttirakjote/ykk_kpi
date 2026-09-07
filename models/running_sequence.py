from odoo import _, api, models
from odoo.exceptions import ValidationError


class KpiTemplate(models.Model):
    _inherit = "ykk.kpi.template"

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", "New") == "New":
                department_id = vals.get("department_id")
                period_id = vals.get("period_id")
                company_id = vals.get("company_id") or self.env.company.id
                if not period_id:
                    raise ValidationError(
                        _("Please select a Period before creating a Template KPI.")
                    )
                period = self.env["ykk.kpi.period"].browse(period_id).exists()
                if not period:
                    raise ValidationError(_("The selected Period does not exist."))

                sequence_setting = self.env["ykk.kpi.sequence.setting"].search(
                    [
                        ("department_id", "=", department_id),
                        ("menu", "=", "template_kpi"),
                        ("company_id", "=", company_id),
                        ("active", "=", True),
                        ("sequence_id", "!=", False),
                    ],
                    order="id desc",
                    limit=1,
                )
                if not sequence_setting:
                    department = self.env["hr.department"].browse(department_id)
                    raise ValidationError(
                        _(
                            "Please configure a Sequence Setting for Template KPI "
                            "and department %s."
                        )
                        % department.display_name
                    )

                sequence_number = sequence_setting.sequence_id.next_by_id()
                if not sequence_number:
                    raise ValidationError(
                        _("Unable to generate the Template KPI sequence number.")
                    )

                vals["name"] = (
                    "%s-%s" % (sequence_number, period.suffix)
                    if period.suffix
                    else sequence_number
                )
        return super().create(vals_list)


class KpiAnnualKpi(models.Model):
    _inherit = "ykk.kpi.annual.kpi"

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", "New") == "New":
                annual_kpi = self.new(vals)
                employee = annual_kpi.employee_id
                department = employee.department_id
                period = annual_kpi.period_id
                company = annual_kpi.company_id or self.env.company

                if not employee:
                    raise ValidationError(
                        _("Please select an Employee before creating an KPI/Goal Setting.")
                    )
                if not department:
                    raise ValidationError(
                        _("The selected Employee does not have a Department.")
                    )
                if not period:
                    raise ValidationError(
                        _("Please select a Period before creating an KPI/Goal Setting.")
                    )

                sequence_setting = self.env["ykk.kpi.sequence.setting"].search(
                    [
                        ("department_id", "=", department.id),
                        ("menu", "=", "annual_kpi"),
                        ("company_id", "=", company.id),
                        ("active", "=", True),
                        ("sequence_id", "!=", False),
                    ],
                    order="id desc",
                    limit=1,
                )
                if not sequence_setting:
                    raise ValidationError(
                        _(
                            "Please configure a Sequence Setting for KPI/Goal Setting "
                            "and department %s."
                        )
                        % department.display_name
                    )

                sequence_number = sequence_setting.sequence_id.next_by_id()
                if not sequence_number:
                    raise ValidationError(
                        _("Unable to generate the KPI/Goal Setting sequence number.")
                    )

                vals["name"] = (
                    "%s-%s" % (sequence_number, period.suffix)
                    if period.suffix
                    else sequence_number
                )
        return super().create(vals_list)


class KpiDepartmentKpi(models.Model):
    _inherit = "ykk.kpi.department.kpi"

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", "New") == "New":
                evaluation = self.new(vals)
                employee = evaluation.employee_id
                department = employee.department_id
                period = evaluation.period_id
                company = evaluation.company_id or self.env.company

                if not employee:
                    raise ValidationError(
                        _("Please select an Employee before creating an Evaluation.")
                    )
                if not department:
                    raise ValidationError(
                        _("The selected Employee does not have a Department.")
                    )
                if not period:
                    raise ValidationError(
                        _("Please select a Period before creating an Evaluation.")
                    )

                self._validate_unique_employee_period(employee.id, period.id)

                sequence_setting = self.env["ykk.kpi.sequence.setting"].search(
                    [
                        ("department_id", "=", department.id),
                        ("menu", "=", "department_kpi"),
                        ("company_id", "=", company.id),
                        ("active", "=", True),
                        ("sequence_id", "!=", False),
                    ],
                    order="id desc",
                    limit=1,
                )
                if not sequence_setting:
                    raise ValidationError(
                        _(
                            "Please configure a Sequence Setting for Evaluation "
                            "and department %s."
                        )
                        % department.display_name
                    )

                sequence_number = sequence_setting.sequence_id.next_by_id()
                if not sequence_number:
                    raise ValidationError(
                        _("Unable to generate the Evaluation sequence number.")
                    )

                vals["name"] = (
                    "%s-%s" % (sequence_number, period.suffix)
                    if period.suffix
                    else sequence_number
                )
        return super().create(vals_list)
