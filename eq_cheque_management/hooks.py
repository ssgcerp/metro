# -*- coding: utf-8 -*-

def post_init_hook(env):
    """Create cheque configuration for all existing companies"""
    # Get all companies
    companies = env['res.company'].search([])
    
    # Get default sequences
    incoming_sequence = env['ir.sequence'].search([
        ('code', '=', 'eq.cheque.incoming')
    ], limit=1)
    
    outgoing_sequence = env['ir.sequence'].search([
        ('code', '=', 'eq.cheque.outgoing')
    ], limit=1)
    
    # Create configuration for each company if it doesn't exist
    for company in companies:
        config = env['eq.cheque.config'].search([
            ('company_id', '=', company.id)
        ], limit=1)
        
        if not config:
            env['eq.cheque.config'].create({
                'company_id': company.id,
                'incoming_sequence_id': incoming_sequence.id if incoming_sequence else False,
                'outgoing_sequence_id': outgoing_sequence.id if outgoing_sequence else False,
            })

