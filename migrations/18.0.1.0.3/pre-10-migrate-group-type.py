import logging


_logger = logging.getLogger(__name__)


def migrate(cr, version):
    cr.execute(
        """
        UPDATE ykk_kpi_goal
           SET group_type = 'department'
         WHERE group_type = 'section'
        """
    )
    goal_count = cr.rowcount

    cr.execute(
        """
        UPDATE ykk_kpi_hr_evaluation
           SET group_type = 'department'
         WHERE group_type = 'section'
        """
    )
    hr_evaluation_count = cr.rowcount

    _logger.info(
        "Migrated group_type from section to department: "
        "%s KPI Goal record(s), %s HR Evaluation record(s).",
        goal_count,
        hr_evaluation_count,
    )
