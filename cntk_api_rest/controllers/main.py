# -*- coding: utf-8 -*-
from odoo import http, fields
import json
from odoo.http import request
import logging
from odoo.exceptions import AccessError, UserError
from datetime import datetime, timedelta
from collections import defaultdict

class HttpIntegrateController(http.Controller):
    _logger = logging.getLogger(__name__)

    def _prepare_response(self, status, message, data):
        return {
            'status': status,
            'message': message,
            'data': data
        }

    def _search_records(self, model, domain):
        return request.env[model].search(domain)

    def _prepare_order_json(self, order):
        return {
            'id': order.id,
            'user_id': order.user_id.id,
            'name': order.name,
            'date_order': order.date_order,
            'partner_id': order.partner_id.id,
            'partner_name': order.partner_id.name,
            'amount_total': order.amount_total,
            'state': order.state,
            'order_line': [
                {
                    'product_id': line.product_id.id,
                    'product_name': line.product_id.name,
                    'price_unit': line.price_unit,
                    'product_uom_qty': line.product_uom_qty,
                    'price_subtotal': line.price_subtotal,
                } for line in order.order_line
            ]
        }

    @http.route('/costumers', type='jsonrpc', auth='user', methods=['GET'], csrf=False)
    def costumers(self, **kwargs):
        name = kwargs.get('name')
        self._logger.info(f"costumer: {name}")
        domain = [('customer_rank', '>', 0)]
        if name:
            domain.append(('name', 'ilike', name))
        customers = self._search_records('res.partner', domain)
        customersjson = [{'id': customer.id, 'name': customer.name, 'rfc': customer.vat} for customer in customers]
        return self._prepare_response('success', 'API request received with authentication cookie session_id', {'customers': customersjson})

    @http.route('/products', type='jsonrpc', auth='user', methods=['GET'], csrf=False)
    def products(self, **kwargs):
        name = kwargs.get('name')
        self._logger.info(f"product: {name}")
        domain = [('sale_ok', '=', True)]
        if name:
            domain.append(('name', 'ilike', name))
        products = self._search_records('product.product', domain)
        productsjson = [{'id': product.id, 'name': product.name} for product in products]
        return self._prepare_response('success', 'API request received with authentication cookie session_id', {'products': productsjson})

    @http.route('/order', type='jsonrpc', auth='user', methods=['POST'], csrf=False)
    def create_order(self, **kwargs):
        self._logger.info(f"create_order: {kwargs}")
        if kwargs:
            response = http.request.env['sale.order'].sudo().create(kwargs)
        return self._prepare_response('success', 'Order created successfully', {'order_id': response.id})

    @http.route('/order', type='jsonrpc', auth='user', methods=['GET'], csrf=False)
    def search_order(self, **kwargs):
        self._logger.info(f"order: {kwargs}")
        query = []
        if 'id' in kwargs:
            query.append(('id', '=', kwargs['id']))
        if 'user_id' in kwargs:
            query.append(('user_id', '=', kwargs['user_id']))
        if 'partner_id' in kwargs:
            query.append(('partner_id', '=', kwargs['partner_id']))
        if 'name' in kwargs:
            query.append(('name', 'ilike', kwargs['name']))
        if 'from' in kwargs and 'to' in kwargs:
            query.append(('create_date', '>=', kwargs['from']))
            query.append(('create_date', '<=', kwargs['to']))
        self._logger.info(query)
        orders = self._search_records('sale.order', query)
        ordersjson = [self._prepare_order_json(order) for order in orders]
        return self._prepare_response('success', 'API request received with authentication cookie session_id', {'orders': ordersjson})

    @http.route('/pruebasa', type='jsonrpc', auth='public', methods=['GET'], csrf=False)
    def pruebasa(self, **kwargs):
        parameters = json.loads(http.request.httprequest.data)
        return self._prepare_response('success', 'API PUBLIC request', {'parameters': parameters})
    

    @http.route('/attendance/checkinout', type='jsonrpc', auth='user', methods=['POST'], csrf=False)
    def change_attendance(self, **post):
        """
        API to perform attendance check in/out
        JSON Body:
        {
            "employee_id": 5,
            "geo_information": {
                "location_id": 2,
                "lat": "12.3456",
                "long": "78.9012"
            },
            "notes": "Working on foundation",
            "work_type": "Onsite",
            "project_name": "Site A",
            "device_name": "Samsung Galaxy Tab"
        }
        """
        employee_id = post.get('employee_id')
        geo_information = post.get('geo_information') or {}
        notes = post.get('notes')
        work_type = post.get('work_type')
        project_name = post.get('project_name')
        device_name = post.get('device_name')

        if not employee_id:
            return {"error": "Missing employee_id"}

        employee = request.env['hr.employee'].sudo().browse(employee_id)
        if not employee.exists():
            return {"error": "Employee not found"}

        try:
            action_date = fields.Datetime.now()

            if employee.attendance_state != 'checked_in':
                # Check In
                vals = {
                    'employee_id': employee.id,
                    'check_in': action_date,
                    'in_device': device_name,
                    'in_notes': notes,
                    'in_work_type': work_type,
                    'in_project_name': project_name,
                }

                location_id = geo_information.get("location_id")
                if location_id:
                    comp_location = request.env['hr.attendance.location'].sudo().browse(location_id)
                    if not comp_location:
                        return {"error": _("Location attendance not found!")}

                    if comp_location.main_location and request.env.user.restrict_attendance:
                        whitelist_ip = request.env['ir.config_parameter'].sudo().get_param("whitelist_ip", "[]")
                        import json
                        whitelist_ip = json.loads(whitelist_ip) if isinstance(whitelist_ip, str) else whitelist_ip

                        if request.httprequest.environ['REMOTE_ADDR'] not in whitelist_ip:
                            raise AccessError(_("You are not allowed to check in outside the company's IP range!"))

                    vals['attendance_location'] = comp_location.id

                    for key in geo_information:
                        if key != 'location_id':
                            vals['in_%s' % key] = geo_information[key]

                attendance = request.env['hr.attendance'].sudo().create(vals)
                return {"status": "checked_in", "attendance_id": attendance.id}

            else:
                # Check Out
                attendance = request.env['hr.attendance'].sudo().search([
                    ('employee_id', '=', employee.id),
                    ('check_out', '=', False)
                ], limit=1)

                if not attendance:
                    raise UserError(_(
                        'Cannot perform check out on %(empl_name)s, could not find corresponding check in. '
                        'Your attendances have probably been modified manually by human resources.',
                        empl_name=employee.sudo().name))

                write_vals = {
                    'check_out': action_date,
                    'out_device': device_name,
                    'out_notes': notes,
                    'out_work_type': work_type,
                    'out_project_name': project_name,
                }

                for key in geo_information:
                    if key != 'location_id':
                        write_vals['out_%s' % key] = geo_information[key]

                attendance.write(write_vals)
                return {"status": "checked_out", "attendance_id": attendance.id}

        except Exception as e:
            return {"error": str(e)}
        

    @http.route('/attendance/checkin-status', type='jsonrpc', auth='user', methods=['POST'], csrf=False)
    def attendance_checkin_status(self, **post):
        """
        API to check if an employee is already checked in based on user_id

        JSON Body:
        {
            "user_id": 7
        }

        Response:
        {
            "already_checkin": true,
            "attendance_details": {
                "id": 42,
                "check_in": "2025-04-12 09:00:00",
                "project_name": "Site A",
                "notes": "Morning check-in",
                ...
            }
        }
        """
        user_id = post.get('user_id')

        if not user_id:
            return {"error": "Missing user_id"}

        user = request.env['res.users'].sudo().browse(user_id)
        if not user.exists():
            return {"error": "User not found"}

        employee = request.env['hr.employee'].sudo().search([('user_id', '=', user_id)], limit=1)
        if not employee:
            return {"error": "Employee not found for the given user_id"}

        attendance = request.env['hr.attendance'].sudo().search([
            ('employee_id', '=', employee.id),
            ('check_out', '=', False)
        ], limit=1)

        if attendance:
            return {
                "already_checkin": True,
                "attendance_details": {
                    "id": attendance.id,
                    "check_in": attendance.check_in,
                    "in_device": attendance.in_device,
                    "in_project_name": attendance.in_project_name,
                    "in_notes": attendance.in_notes,
                    "in_work_type": attendance.in_work_type,
                    "attendance_location_id": attendance.attendance_location.id if attendance.attendance_location else False,
                    "clockin_latitude": attendance.in_latitude,
                    "clockin_longitude": attendance.in_longitude,
                    "employee_id": attendance.employee_id.id,
                }
            }
        else:
            return {"already_checkin": False}
        
    @http.route('/attendance/last_7_days', type='jsonrpc', auth='user', methods=['POST'], csrf=False)
    def get_attendance_last_7_days(self, **post):
        """
        API to fetch the last 7 days of attendance for an employee using user_id
        Grouped by day (check_in date)

        Input JSON:
        {
            "user_id": 7
        }

        Output JSON:
        {
            "2025-04-05": [
                {
                    "id": 42,
                    "check_in": "...",
                    "check_out": "...",
                    "project": "...",
                    "device": "..."
                }
            ],
            ...
        }
        """
        user_id = post.get('user_id')
        if not user_id:
            return {"error": "Missing user_id"}

        user = request.env['res.users'].sudo().browse(user_id)
        if not user.exists():
            return {"error": "User not found"}

        employee = request.env['hr.employee'].sudo().search([('user_id', '=', user_id)], limit=1)
        if not employee:
            return {"error": "Employee not linked to user"}

        today = datetime.today()
        seven_days_ago = today - timedelta(days=7)

        attendances = request.env['hr.attendance'].sudo().search([
            ('employee_id', '=', employee.id),
            ('check_in', '>=', seven_days_ago.strftime('%Y-%m-%d 00:00:00'))
        ], order='check_in desc')

        result = defaultdict(list)
        for att in attendances:
            check_in_date = att.check_in.date().strftime('%Y-%m-%d')
            result[check_in_date].append({
                "id": att.id,
                "check_in": att.check_in,
                "check_out": att.check_out,
                "in_project": att.in_project_name or "",
                "in_device": att.in_device or "",
                "in_notes": att.in_notes or "",
                "in_work_type": att.in_work_type or "",
                "in_latitude": att.in_latitude or 0.0,
                "in_longitude": att.in_longitude or 0.0,
            })

        return result
    
    @http.route('/attendance/checkin-upload', type='jsonrpc', auth='user', methods=['POST'], csrf=False)
    def api_checkin_employee(self, **post):
        """
        API to create a new check-in attendance record

        Expected Input JSON:
        {
            "user_id": 7,
            "check_in": "2025-04-12 08:55:00",
            "in_device": "Android",
            "clockin_latitude": 23.456,
            "clockin_longitude": 72.789,
            "in_notes": "Arrived on site",
            "in_project_name": "Tower A",
            "in_activiy_name": "Inspection",
            "location_id": "2"
        }
        """

        user_id = post.get("user_id")
        check_in = post.get("check_in")
        in_device = post.get("in_device")
        in_latitude = post.get("clockin_latitude")
        in_longitude = post.get("clockin_longitude")
        in_notes = post.get("in_notes", "")
        in_project_name = post.get("in_project_name", "")
        in_work_type = post.get("in_activiy_name", "")
        geo_information = {
            "latitude": post.get("clockin_latitude"),
            "longitude": post.get("clockin_longitude"),
            "location_id": post.get("location_id")
        }

        if not user_id or not check_in:
            return {"error": "Missing required parameters: user_id or check_in"}

        user = request.env['res.users'].sudo().browse(int(user_id))
        if not user.exists():
            return {"error": "User not found"}

        employee = request.env['hr.employee'].sudo().search([('user_id', '=', user_id)], limit=1)
        if not employee:
            return {"error": "Employee not found for user_id"}

        # Check for existing open attendance (prevent multiple check-ins)
        existing_attendance = request.env['hr.attendance'].sudo().search([
            ('employee_id', '=', employee.id),
            ('check_out', '=', False)
        ], limit=1)

        if existing_attendance:
            return {"error": "Already checked in. Please check out first."}

        

        # Parse check-in datetime
        try:
            check_in_dt = datetime.strptime(check_in, '%Y-%m-%d %H:%M:%S')
        except Exception as e:
            return {"error": f"Invalid datetime format for check_in. Use 'YYYY-MM-DD HH:MM:SS'. Details: {str(e)}"}

        vals = {
            'employee_id': employee.id,
            'check_in': check_in,
            'in_device': in_device,
            'in_notes': in_notes,
            'in_work_type': in_work_type,
            'in_project_name': in_project_name,
        }   

        location_id = geo_information.get("location_id")
        if location_id:
            comp_location = request.env['hr.attendance.location'].sudo().browse(int(location_id))
            if not comp_location:
                return {"error": _("Location attendance not found!")}

            # IP Restriction check
            if comp_location.main_location and request.env.user.restrict_attendance:
                whitelist_ip = request.env['ir.config_parameter'].sudo().get_param("whitelist_ip", "[]")
                import json
                whitelist_ip = json.loads(whitelist_ip) if isinstance(whitelist_ip, str) else whitelist_ip

                user_ip = request.httprequest.environ.get('REMOTE_ADDR')
                if user_ip not in whitelist_ip:
                    raise AccessError(_("You are not allowed to check in outside the company's IP range!"))

            vals['attendance_location'] = comp_location.id

            for key in geo_information:
                if key != 'location_id' and geo_information[key] is not None:
                    vals['in_%s' % key] = geo_information[key]

        attendance = request.env['hr.attendance'].sudo().create(vals)
        employee.attendance_state = 'checked_in'

        return {
            "status": "checked_in",
            "attendance_id": attendance.id,
            "employee": employee.attendance_state,
            "check_in": attendance.check_in
        }

    
    @http.route('/attendance/checkout', type='jsonrpc', auth='user', methods=['POST'], csrf=False)
    def api_checkout_employee(self, **post):
        """
        API to perform attendance check-out using attendance ID (online_log_id)

        Expected JSON:
        {
            "params": {
                "user_id": 7,
                "online_log_id": 123,
                "check_out": "2025-04-12 18:00:00",
                "out_device": "Android",
                "clockout_latitude": 23.456,
                "clockout_longitude": 72.789
            }
        }
        """
        user_id = post.get("user_id")
        attendance_id = post.get("online_log_id")  # This is hr.attendance ID
        check_out = post.get("check_out")
        out_device = post.get("out_device")
        out_latitude = post.get("clockout_latitude")
        out_longitude = post.get("clockout_longitude")

        if not user_id or not attendance_id or not check_out:
            return {"error": "Missing required fields: user_id, online_log_id, or check_out"}

        # Get the employee from user
        employee = request.env['hr.employee'].sudo().search([('user_id', '=', user_id)], limit=1)
        if not employee:
            return {"error": "Employee not found for user_id"}

        # Get the attendance record by ID
        attendance = request.env['hr.attendance'].sudo().browse(attendance_id)
        if not attendance or attendance.employee_id.id != employee.id:
            return {"error": "Attendance record not found or doesn't belong to this employee"}

        if attendance.check_out:
            return {"error": "This attendance is already checked out"}

        try:
            check_out_dt = datetime.strptime(check_out, '%Y-%m-%d %H:%M:%S')
        except Exception as e:
            return {"error": f"Invalid datetime format for check_out. Use 'YYYY-MM-DD HH:MM:SS'. Details: {str(e)}"}

        # Update the attendance record
        attendance.write({
            'check_out': check_out_dt,
            'out_device': out_device,
            'out_latitude': out_latitude,
            'out_longitude': out_longitude,
        })

        return {
            "success": True,
            "attendance_log_id": attendance.id,
            "employee": employee.name,
            "check_in": attendance.check_in,
            "check_out": attendance.check_out
        }

