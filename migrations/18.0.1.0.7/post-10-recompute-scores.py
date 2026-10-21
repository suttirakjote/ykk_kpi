from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    """Refresh stored totals after Odoo converts the score columns to integers."""
    env = api.Environment(cr, SUPERUSER_ID, {})
    for line_type in ("interview", "performance", "role", "behavior"):
        model = env[f"ykk.kpi.department.kpi.{line_type}.line"]
        last_id = 0
        while True:
            lines = model.search([("id", ">", last_id)], order="id", limit=1000)
            if not lines:
                break
            lines._compute_total_score()
            # Flush also recomputes the dependent stored department totals.
            env.flush_all()
            last_id = lines[-1].id
