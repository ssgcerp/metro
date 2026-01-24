from odoo import models, fields, api

class ProjectTaskWizard(models.TransientModel):
    _name = 'project.task.wizard'
    _description = 'Task Details Wizard'

    task_id = fields.Many2one('project.task', string="Task", required=True)
    name = fields.Char(related='task_id.name', readonly=True)
    attachment_ids = fields.Many2many('ir.attachment', string="Attachments", 
                                      relation="project_task_wizard_attachment_rel", 
                                      column1="wizard_id", column2="attachment_id")

    @api.model
    def default_get(self, fields_list):
        """Pre-load existing attachments when opening the wizard."""
        res = super().default_get(fields_list)
        task_id = self.env.context.get('default_task_id')
        if task_id:
            task = self.env['project.task'].browse(task_id)
            res.update({
                'task_id': task.id,
                'name':task.name,
                'attachment_ids': [(6, 0, task.attachment_ids.ids)],  
            })
        return res

    def action_save(self):
        """Save uploaded documents and remove deleted ones."""
        if self.task_id:
            existing_attachments = self.env['ir.attachment'].search([
                ('res_model', '=', 'project.task'),
                ('res_id', '=', self.task_id.id)
            ])
            attachments_to_delete = existing_attachments - self.attachment_ids

            attachments_to_delete.unlink()
            for attachment in self.attachment_ids:
                attachment.write({
                    'res_model': 'project.task',
                    'res_id': self.task_id.id,
                })

        return {'type': 'ir.actions.act_window_close'}
