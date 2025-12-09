# Copyright 2020 Eugene Molotov <https://it-projects.info/team/em230418>
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl.html).

import base64

from odoo import http
from odoo.http import request
from odoo.tools.image import image_process, image_guess_size_from_field_name

from odoo.addons.web.controllers.binary import Binary


class BinaryExtended(Binary):
    @http.route([
        '/web/image',
        '/web/image/<string:xmlid>',
        '/web/image/<string:xmlid>/<string:filename>',
        '/web/image/<string:xmlid>/<int:width>x<int:height>',
        '/web/image/<string:xmlid>/<int:width>x<int:height>/<string:filename>',
        '/web/image/<string:model>/<int:id>/<string:field>',
        '/web/image/<string:model>/<int:id>/<string:field>/<int:width>x<int:height>',
        '/web/image/<string:model>/<int:id>/<string:field>/<int:width>x<int:height>/<string:filename>',
    ], type='http', auth="public", readonly=True)
    def content_image(self, xmlid=None, model='ir.attachment', id=None, field='raw',
                      filename_field='name', filename=None, mimetype=None, unique=False,
                      download=False, width=0, height=0, crop=False, access_token=None,
                      nocache=False, quality=0):
        # Check if we need to handle URL redirects (302 status)
        try:
            status, headers, image_base64 = request.env["ir.http"].binary_content(
                xmlid=xmlid,
                model=model,
                id=id and int(id),
                field=field,
                unique=unique,
                filename=filename,
                filename_field=filename_field,
                download=download,
                mimetype=mimetype,
                default_mimetype="image/png",
                access_token=access_token,
            )

            if status in [301, 302, 304] or (status != 200 and download):
                # em230418: added 302 only - handle redirects for URL attachments
                return request.env["ir.http"]._response_by_status(
                    status, headers, image_base64
                )
        except Exception:
            # If binary_content fails, fall through to parent implementation
            pass

        # For normal cases, call parent implementation
        return super(BinaryExtended, self).content_image(
            xmlid=xmlid,
            model=model,
            id=id,
            field=field,
            filename_field=filename_field,
            filename=filename,
            mimetype=mimetype,
            unique=unique,
            download=download,
            width=width,
            height=height,
            crop=crop,
            access_token=access_token,
            nocache=nocache,
        )
