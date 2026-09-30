import logging


_logger = logging.getLogger(__name__)


def migrate(cr, version):
    tables = [
        "ykk_kpi_department_kpi_interview_line",
        "ykk_kpi_department_kpi_performance_line",
        "ykk_kpi_department_kpi_role_line",
        "ykk_kpi_department_kpi_behavior_line",
    ]

    for table in tables:
        cr.execute(
            """
            SELECT data_type
              FROM information_schema.columns
             WHERE table_schema = current_schema()
               AND table_name = %s
               AND column_name = 'performance_result'
            """,
            [table],
        )
        column = cr.fetchone()
        if not column or column[0] == "double precision":
            continue

        cr.execute(
            f"""
            SELECT COUNT(*)
              FROM "{table}"
             WHERE performance_result IS NOT NULL
               AND BTRIM(performance_result) != ''
               AND BTRIM(performance_result) !~
                   '^[+-]?([0-9]+([.][0-9]*)?|[.][0-9]+)([eE][+-]?[0-9]+)?$'
            """
        )
        invalid_count = cr.fetchone()[0]

        cr.execute(
            f"""
            ALTER TABLE "{table}"
            ALTER COLUMN performance_result TYPE DOUBLE PRECISION
            USING CASE
                WHEN performance_result IS NOT NULL
                 AND BTRIM(performance_result) ~
                     '^[+-]?([0-9]+([.][0-9]*)?|[.][0-9]+)([eE][+-]?[0-9]+)?$'
                THEN BTRIM(performance_result)::DOUBLE PRECISION
                ELSE 0.0
            END
            """
        )

        _logger.info(
            "Converted %s.performance_result to double precision; "
            "%s non-numeric value(s) were replaced with 0.0.",
            table,
            invalid_count,
        )
