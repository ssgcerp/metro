from odoo import api, SUPERUSER_ID


def post_init_hook(env):
    """Ensure existing projects have a draft stage assigned."""
    # In Odoo 19, post_init_hook receives env directly
    Stage = env['fc.project.stage'].sudo().with_context(active_test=False)
    Project = env['project.project'].sudo().with_context(active_test=False)

    draft_stage = Stage.search([('is_draft_stage', '=', True)], limit=1)
    if not draft_stage:
        return

    projects_without_stage = Project.search([('fc_stage_id', '=', False)])
    if projects_without_stage:
        projects_without_stage.write({'fc_stage_id': draft_stage.id})
    env.cr.commit()

