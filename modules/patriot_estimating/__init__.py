from . import models


def _populate_crew_members(env):
    """Post-init hook: add members to Crew A by looking up employees by name."""
    crew_a = env.ref('patriot_estimating.crew_a', raise_if_not_found=False)
    if not crew_a or crew_a.member_ids:
        return  # Already populated or crew doesn't exist

    CrewMember = env['ps.install.crew.member']
    employees = {
        'Robert S. Barcum': 25.0,
        'Bryson Tate': 15.0,
    }
    for emp_name, rate in employees.items():
        emp = env['hr.employee'].search([('name', '=', emp_name)], limit=1)
        if emp:
            CrewMember.create({
                'crew_id': crew_a.id,
                'employee_id': emp.id,
                'hourly_rate': rate,
            })
