# -*- coding: utf-8 -*-
################################################################################
#
#    A part of OpenHRMS Project <https://www.openhrms.com>
#
#    Copyright (C) 2024-TODAY Cybrosys Technologies(<https://www.cybrosys.com>).
#    Author: Cybrosys Techno Solutions (odoo@cybrosys.com)
#
#    This program is under the terms of the Odoo Proprietary License v1.0
#    (OPL-1)
#    It is forbidden to publish, distribute, sublicense, or sell copies of the
#    Software or modified copies of the Software.
#
#    THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
#    IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
#    FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
#    IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM,
#    DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR
#    OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE
#    USE OR OTHER DEALINGS IN THE SOFTWARE.
#
################################################################################

from odoo import models, api


class ProjectProject(models.Model):
    _inherit = 'project.project'

    @api.model
    def _fix_missing_partner_ids(self):
        """Set a default partner_id for projects that don't have one.
        This prevents validation errors when partner_id becomes required."""
        projects_without_partner = self.search([('partner_id', '=', False)])
        if projects_without_partner:
            # Use company's partner as default, or create a generic one
            for project in projects_without_partner:
                if project.company_id and project.company_id.partner_id:
                    project.partner_id = project.company_id.partner_id
                else:
                    # Fallback: use the first partner or company partner
                    default_partner = self.env['res.partner'].search([], limit=1)
                    if default_partner:
                        project.partner_id = default_partner
        return True

