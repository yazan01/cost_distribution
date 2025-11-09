from collections import OrderedDict
import frappe
from frappe import _, _dict
from frappe.utils import cstr, getdate
from datetime import datetime, timedelta

from erpnext import get_company_currency, get_default_company
from erpnext.accounts.doctype.accounting_dimension.accounting_dimension import (
    get_accounting_dimensions,
    get_dimension_with_children,
)
from erpnext.accounts.report.financial_statements import get_cost_centers_with_children
from erpnext.accounts.report.utils import convert_to_presentation_currency, get_currency
from erpnext.accounts.utils import get_account_currency


def execute(filters=None):
    user = frappe.session.user

    role = frappe.db.sql("""SELECT `role` FROM `tabHas Role` WHERE parent=%(user)s""",{"user": user}, as_list=True)
    roles = [r[0] for r in role]
    #if "CEO" in frappe.get_roles(user):
    if "CEO" in roles:
        accessible_projects = frappe.get_all('Project', fields=['name'])
        accessible_projects_list_1 = [project['name'] for project in accessible_projects]
    elif "Accounts Manager" in roles:
        accessible_projects = frappe.get_all('Project', fields=['name'])
        accessible_projects_list_1 = [project['name'] for project in accessible_projects]
    elif "Projects Manager" in roles:
        accessible_projects = frappe.get_all('Project', filters={'_assign': ['like', '%' + user + '%']}, fields=['name'])
        accessible_projects_list_1 = [project['name'] for project in accessible_projects]
    else:
        accessible_projects = frappe.db.sql("SELECT name FROM `tabProject`", as_list=True)
        accessible_projects_list_1 = [project[0] for project in accessible_projects]

    selected_projects = filters.get("project")
    if not selected_projects:
        accessible_projects_list = accessible_projects_list_1
    else:
        accessible_projects_list = selected_projects
    
    select_partner = filters.get("partner")
    if not select_partner:
        # If no partner is selected, get all employees and assign to select_partner
        select_partner = frappe.db.sql("SELECT name FROM `tabEmployee`", as_list=True)
        select_partner = [employee[0] for employee in select_partner]
    else:
        select_partner = [select_partner]

    project_type = filters.get("project_type")
    if project_type:
        project_type_array = [project_type]
    else:
        type = frappe.db.sql("SELECT name FROM `tabProject Type`", as_list=True)
        project_type_array = [types[0] for types in type]
	
    data_1 = frappe.db.sql("""
       SELECT 
	    NULL AS 'Account',
	    ctc.posting_date AS 'Posting Date',
	    psc.project AS 'Project',
	    pro.project_name AS 'Project Name',
	    psc.cost_center AS 'Cost Center',
	    cost.employee AS 'Employee',
	    cost.employee_name AS 'Employee Name',
	    cost.employment_type AS 'Employee Type',
	    cost.designation AS 'Designation',
	    cost.level AS 'Level',
        psc.status AS 'Status',
	    cost.ctc AS 'Level CTC',
	    CASE 
	        WHEN cost.total_hours = 0 THEN 1
	        ELSE CASE
	                 WHEN cost.employment_type = 'Permanent' THEN cost.total_hours
	                 ELSE cost.total_hours
	             END
	    END AS 'Total Hours',
	    (psc.total_cost_of_project/psc.total_hours) AS 'Hours Rate',
	    psc.total_hours AS 'Hours',
	    psc.total_cost_of_project AS 'Total',            
	    pro.project_type AS 'Project Type',
	    pro.project_manager AS 'Manager',
	    pro.project_manager_name AS 'Manager Name',            
	    ctc.name AS 'CTC'           
	FROM
	    `tabCTC Distribution` AS ctc
	JOIN
	    `tabEmployee Cost Table CTC` AS cost
	ON
	    ctc.name = cost.parent
	JOIN
	    `tabProject Summary CTC` AS psc
	ON
	    ctc.name = psc.parent AND cost.employee = psc.employee 
	JOIN
	    `tabProject` AS pro
	ON
	    psc.project = pro.name
	WHERE
	    ctc.docstatus = 1
	    AND ctc.posting_date BETWEEN %(from_date)s AND %(to_date)s
	    AND psc.project IN %(accessible_projects)s
	    AND cost.docstatus = 1
	    AND pro.project_manager IN %(manager)s
	    AND pro.project_type IN %(type)s

        UNION ALL

        SELECT
            afc.account AS 'Account',
            NULL AS 'Posting Date',
            gl.project AS 'Project',
            pro.project_name AS 'Project Name',
            gl.cost_center AS 'Cost Center',
            NULL AS 'Employee',
            NULL AS 'Employee Name',
            NULL AS 'Employee Type',
            NULL AS 'Designation',
            NULL AS 'Level',
            NULL AS 'Status',
            NULL AS 'Level CTC',
            NULL AS 'Total Hours',
            NULL AS 'Hours Rate',
            NULL AS 'Hours',
            (SUM(gl.debit) - SUM(gl.credit)) * afc.currency AS 'Total',            
            pro.project_type AS 'Project Type',
            pro.project_manager AS 'Manager',
            pro.project_manager_name AS 'Manager Name',            
            NULL AS 'CTC'            
        FROM
            `tabAccounts For CTC` AS afc
        JOIN
            `tabGL Entry` AS gl
        ON
            afc.account = gl.account
        JOIN
            `tabProject` AS pro
        ON
            gl.project = pro.name
        WHERE
            afc.type = 'Indirect'
            AND gl.docstatus = 1
            AND gl.is_cancelled = 0
            AND gl.project IN %(accessible_projects)s
            AND gl.posting_date BETWEEN %(from_date)s AND %(to_date)s
			AND pro.project_manager IN %(manager)s
			AND pro.project_type IN %(type)s
            AND gl.remarks NOT REGEXP "Cost Distribution" AND gl.remarks NOT REGEXP "CAPITALIZATION"
        GROUP BY
            afc.account, gl.project;
    """, {
        "accessible_projects": accessible_projects_list,
        "from_date": filters.get("from_date"),
        "to_date": filters.get("to_date"),
		"manager": select_partner,
		"type": project_type_array
    }, as_dict=True)

    ##########################################################################

    for record in data_1:
        if record.get('Employee Type') == 'Permanent':
            ctc = record['CTC']
            emp = record['Employee']

            exeption_level = frappe.db.sql("""
                SELECT new_level FROM `tabCTC Employee Exception` 
                WHERE parent = %s AND employee = %s
            """, (ctc, emp), as_dict=True)

            if exeption_level:
                record['Level'] = exeption_level[0].new_level

            employee_level = record['Level']
            project = record['Project']
            status = record['Status']

            ctc_d = frappe.db.sql("""
                SELECT from_date, to_date, company FROM `tabCTC Distribution` 
                WHERE name = %s
            """, (ctc), as_dict=True)

            if ctc_d:
                from_date = ctc_d[0].from_date
                to_date = ctc_d[0].to_date
                ctc_company = ctc_d[0].company

            #start_date = datetime.strptime(from_date, '%Y-%m-%d')
            #end_date = datetime.strptime(to_date, '%Y-%m-%d')
            start_date = from_date
            end_date = to_date
            year = to_date.year 

            current_date = start_date
            number_of_days = 0
            while current_date <= end_date:
                if current_date.weekday() not in (4, 5):
                    number_of_days += 1
                current_date += timedelta(days=1)
            
            
            # Determine the correct level based on status
            if ctc_company != "iValue KSA":
                level_to_search = f"{employee_level}-R"
            else:
                level_to_search = employee_level
            
            # Get the correct CTC for this level and project
            level_proj_ctc = None


            
            # project level with -R if remotely
            if ctc_company != "iValue KSA":
                ctc_result = frappe.db.sql("""
                    SELECT ctc, parent FROM `tabLevel Rate` 
                    WHERE parent = %s AND project = %s AND year = %s
                """, (level_to_search, project, year), as_dict=True)
                
                if ctc_result:
                    level_proj_ctc = ctc_result[0].ctc
                    calculate_level = ctc_result[0].parent
            
            # project level without -R
            if not level_proj_ctc:
                ctc_result = frappe.db.sql("""
                    SELECT ctc, parent FROM `tabLevel Rate` 
                    WHERE parent = %s AND project = %s AND year = %s
                """, (employee_level, project, year), as_dict=True)
                
                if ctc_result:
                    level_proj_ctc = ctc_result[0].ctc
                    calculate_level = ctc_result[0].parent
            
            # level CTC
            if not level_proj_ctc:
                ctc_result = frappe.db.sql("""
                    SELECT ctc, parent FROM `tabLevel Rate` 
                    WHERE parent = %s AND project IS NULL AND year = %s
                """, (employee_level, year), as_dict=True)
                
                if ctc_result:
                    level_proj_ctc = ctc_result[0].ctc
                    calculate_level = ctc_result[0].parent


            
            # Update record with correct values
            if level_proj_ctc:
                # 1. Update Level to show -R if remotely
                record['Level'] = calculate_level
                
                # 2. Update Level CTC with the correct value
                record['Level CTC'] = level_proj_ctc
                
                # 3. Update Total Hours to full working hours in the period
                record['Total Hours'] = (number_of_days*9)
                
                




    ##########################################################################

    assign = filters.get("Assign_to")

    if assign:
        employee = frappe.get_doc('Employee', assign)
        user = frappe.get_doc('User', employee.user_id)
        company_email = user.email

        d1 = frappe.db.sql("""SELECT project, ratio FROM `tabPartner Share Project Table` WHERE parent=%(assign)s;""", {"assign": assign}, as_dict=True)

        project_ratios = {record['project']: record['ratio'] for record in d1}
        data_2 = []
        for record in data_1:
            if record['Project'] in project_ratios:
                adjusted_total = record['Total'] * project_ratios[record['Project']] / 100
                record['Total'] = adjusted_total        
                data_2.append(record)
        data = data_2
    else:
        data = data_1

    revenue = filters.get("revenue")
    indirect_costs = filters.get("indirect_costs")
    ctc = filters.get("ctc")
    
    if revenue == 1 or indirect_costs == 1 or ctc == 1:
        data_show = []
        if revenue == 1:
            for record in data:
                if record['Account'] and record['Account'].startswith("4"):
                    data_show.append(record)

        if indirect_costs == 1:
            for record in data:
                if record['Account'] and record['Account'].startswith("5"):
                    data_show.append(record)

        if ctc == 1:
            for record in data:
                if not record['Account']:
                    data_show.append(record)

        data = data_show
 

    group_by_project = filters.get("group_by_project")

    if group_by_project == 1:
        grouped_data = {}
        
        for record in data:
            project_name = record['Project']
            total = record['Total'] or 0 
            
            if project_name in grouped_data:
                grouped_data[project_name]['Total'] += total
            else:
                grouped_data[project_name] = {
                    "Project": project_name,
                    "Project Name": record['Project Name'],
                    "Project Type": record['Project Type'],
                    "Manager": record['Manager'],
                    "Manager Name": record['Manager Name'],
                    "Cost Center": record['Cost Center'],
                    "Total": total
                }
        
        data = list(grouped_data.values())
        

    columns = [
        {"label": "Account", "fieldname": "Account", "fieldtype": "Data", "width": 200},
        {"label": "Posting Date", "fieldname": "Posting Date", "fieldtype": "Date", "width": 150},
        {"label": "Project", "fieldname": "Project", "fieldtype": "Data", "width": 150},
        {"label": "Project Name", "fieldname": "Project Name", "fieldtype": "Data", "width": 150},
        {"label": "Cost Center", "fieldname": "Cost Center", "fieldtype": "Data", "width": 180},
        {"label": "Employee", "fieldname": "Employee", "fieldtype": "Data", "width": 150},
        {"label": "Employee Name", "fieldname": "Employee Name", "fieldtype": "Data", "width": 150},
        {"label": "Employee Type", "fieldname": "Employee Type", "fieldtype": "Data", "width": 150},
        {"label": "Designation", "fieldname": "Designation", "fieldtype": "Data", "width": 150},
        {"label": "Level", "fieldname": "Level", "fieldtype": "Data", "width": 150},
        {"label": "Level CTC", "fieldname": "Level CTC", "fieldtype": "Data", "width": 150},
        {"label": "Total Hours", "fieldname": "Total Hours", "fieldtype": "Float", "width": 100},
        {"label": "Hours Rate", "fieldname": "Hours Rate", "fieldtype": "Data", "width": 150},
        {"label": "Hours", "fieldname": "Hours", "fieldtype": "Float", "width": 100},
        {"label": "Total", "fieldname": "Total", "fieldtype": "Float", "width": 150},
        {"label": "Project Type", "fieldname": "Project Type", "fieldtype": "Data", "width": 150},
        {"label": "Manager", "fieldname": "Manager", "fieldtype": "Data", "width": 150},
        {"label": "Manager Name", "fieldname": "Manager Name", "fieldtype": "Data", "width": 150},
        {"label": "CTC", "fieldname": "CTC", "fieldtype": "Data", "width": 150}        
    ]

    return columns, data
