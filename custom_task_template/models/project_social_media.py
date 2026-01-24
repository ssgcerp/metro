# -*- coding: utf-8 -*-
from odoo import models, fields,api
from collections import defaultdict
import logging

_logger = logging.getLogger(__name__)

class ProjectSocialMedia(models.Model):
    _name = "project.social.media"
    _description = "Project Social Media Accounts"

    project_id = fields.Many2one('project.project', string="Project", ondelete="cascade")
    social_media_id = fields.Many2one('social.media', string="Social Media", required=True)
    social_account_id = fields.Many2one(
        'social.account', 
        string="Social Account", 
        required=True, 
        domain="[('media_id', '=', social_media_id)]"
    )

class SocialPost(models.Model):
    _inherit = "social.post"

    task_id = fields.Many2one("project.task", string="Related Task", readonly=True)
    project_image = fields.Binary(
        string="Project", 
        compute="_compute_project_image", 
        store=False
    )
    project_id = fields.Many2one("project.project", string="Project")


    @api.depends("task_id", "task_id.project_id")
    def _compute_project_image(self):
        for post in self:
            post.project_image = post.task_id.project_id.image_128 if post.task_id.project_id else False

    @api.model
    def create(self, vals):
        post = super(SocialPost, self).create(vals)

        if self.env.context.get("active_model") == "project.task" and self.env.context.get("active_id"):
            task = self.env["project.task"].browse(self.env.context["active_id"])
            task.write({"social_post_id": post.id})
            post.task_id = task.id

        return post