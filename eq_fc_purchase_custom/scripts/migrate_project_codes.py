# Script to migrate project codes
# Run this in Odoo shell or adapt as a Server Action

def migrate_project_codes(env):
    projects = env['project.project'].search([])
    for project in projects:
        # Check if project_code is empty or just 'DRAFT' (default in fc_project)
        if (not project.project_code or project.project_code == 'DRAFT') and project.name and '(' in project.name and ')' in project.name:
            # Try to match (CODE) pattern at the start
            import re
            match = re.search(r'^\((.*?)\)\s*(.*)', project.name)
            if match:
                code = match.group(1)
                new_name = match.group(2)
                
                print(f"Migrating: {project.name} -> Code: {code}, Name: {new_name}")
                project.write({
                    'project_code': code.strip(),
                    'name': new_name.strip()
                })

# To run in Odoo Shell:
# migrate_project_codes(env)
