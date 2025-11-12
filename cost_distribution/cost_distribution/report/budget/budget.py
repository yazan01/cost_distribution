from collections import OrderedDict
import frappe
from frappe import _, _dict
from frappe.utils import cstr, getdate, flt
from datetime import datetime, timedelta, date


def execute(filters=None):
    if not filters:
        filters = {}
    
    columns = get_columns(filters)
    data = get_data(filters)
    
    return columns, data


def get_columns(filters):
    
    if filters.get("company") == "iValue KSA":
        columns = [
            {"label": _("Employee"), "fieldname": "employee", "fieldtype": "Link", "options": "Employee", "width": 120},
            {"label": _("Employee Name"), "fieldname": "employee_name", "fieldtype": "Data", "width": 150},
            {"label": _("Department"), "fieldname": "department", "fieldtype": "Data", "width": 150},
            {"label": _("Designation"), "fieldname": "designation", "fieldtype": "Link", "options": "Designation", "width": 150},
            {"label": _("Level"), "fieldname": "level", "fieldtype": "Data", "width": 100},
            {"label": _("Company"), "fieldname": "company", "fieldtype": "Link", "options": "Company", "width": 150},
            {"label": _("Gross Pay"), "fieldname": "gross_pay", "fieldtype": "Float", "width": 120},
            {"label": _("Basic"), "fieldname": "basic", "fieldtype": "Float", "width": 120},
            {"label": _("Housing"), "fieldname": "housing", "fieldtype": "Float", "width": 120},
            {"label": _("Nationality"), "fieldname": "nationality", "fieldtype": "Data", "width": 100},
            {"label": _("GOSI amount for the company"), "fieldname": "gosi", "fieldtype": "Float", "width": 150},
            {"label": _("Increment"), "fieldname": "increment", "fieldtype": "Data", "width": 120},
            {"label": _("Promotion"), "fieldname": "promotion", "fieldtype": "Data", "width": 120},
            {"label": _("Medical Insurance / Month"), "fieldname": "medical_insurance", "fieldtype": "Float", "width": 150},
            {"label": _("No of Family"), "fieldname": "no_of_family", "fieldtype": "Int", "width": 100},
            {"label": _("Ticket"), "fieldname": "ticket", "fieldtype": "Float", "width": 120},
            {"label": _("Iqama Cost / Month"), "fieldname": "iqama_cost", "fieldtype": "Data", "width": 150},
            {"label": _("VISA"), "fieldname": "visa", "fieldtype": "Data", "width": 120},
            {"label": _("Training cost / month"), "fieldname": "training_cost", "fieldtype": "Data", "width": 150},
            {"label": _("Penalty"), "fieldname": "penalty", "fieldtype": "Data", "width": 120},
            {"label": _("EOS"), "fieldname": "eos", "fieldtype": "Data", "width": 120},
            {"label": _("Yearly Bonus / Month"), "fieldname": "yearly_bonus", "fieldtype": "Data", "width": 150},
            {"label": _("WHT"), "fieldname": "wht", "fieldtype": "Data", "width": 120},
            {"label": _("Total"), "fieldname": "total", "fieldtype": "Data", "width": 150}
        ]
    elif filters.get("company") == "iValueJOR":
        columns = [
            {"label": _("Employee"), "fieldname": "employee", "fieldtype": "Link", "options": "Employee", "width": 120},
            {"label": _("Employee Name"), "fieldname": "employee_name", "fieldtype": "Data", "width": 150},
            {"label": _("Department"), "fieldname": "department", "fieldtype": "Data", "width": 150},
            {"label": _("Designation"), "fieldname": "designation", "fieldtype": "Link", "options": "Designation", "width": 150},
            {"label": _("Level"), "fieldname": "level", "fieldtype": "Data", "width": 100},
            {"label": _("Company"), "fieldname": "company", "fieldtype": "Link", "options": "Company", "width": 150},
            {"label": _("Gross Pay"), "fieldname": "gross_pay", "fieldtype": "Float", "width": 120},
            {"label": _("Nationality"), "fieldname": "nationality", "fieldtype": "Data", "width": 100},
            
            {"label": _("Social Security amount for the company"), "fieldname": "social_security", "fieldtype": "Float", "width": 150},

            {"label": _("Increment"), "fieldname": "increment", "fieldtype": "Data", "width": 120},
            {"label": _("Promotion"), "fieldname": "promotion", "fieldtype": "Data", "width": 120},
            {"label": _("Medical Insurance / Month"), "fieldname": "medical_insurance", "fieldtype": "Float", "width": 150},
            {"label": _("No of Family"), "fieldname": "no_of_family", "fieldtype": "Int", "width": 100},
            {"label": _("Ticket"), "fieldname": "ticket", "fieldtype": "Float", "width": 120},
            {"label": _("Iqama Cost / Month"), "fieldname": "iqama_cost", "fieldtype": "Data", "width": 150},
            {"label": _("VISA"), "fieldname": "visa", "fieldtype": "Data", "width": 120},
            {"label": _("Training cost / month"), "fieldname": "training_cost", "fieldtype": "Data", "width": 150},
            {"label": _("Penalty"), "fieldname": "penalty", "fieldtype": "Data", "width": 120},
            {"label": _("EOS"), "fieldname": "eos", "fieldtype": "Data", "width": 120},
            {"label": _("Yearly Bonus / Month"), "fieldname": "yearly_bonus", "fieldtype": "Data", "width": 150},
            {"label": _("WHT"), "fieldname": "wht", "fieldtype": "Data", "width": 120},
            {"label": _("Total"), "fieldname": "total", "fieldtype": "Data", "width": 150}
        ]
    elif filters.get("company") == "iValueUAE":
        columns = [
            {"label": _("Employee"), "fieldname": "employee", "fieldtype": "Link", "options": "Employee", "width": 120},
            {"label": _("Employee Name"), "fieldname": "employee_name", "fieldtype": "Data", "width": 150},
            {"label": _("Department"), "fieldname": "department", "fieldtype": "Data", "width": 150},
            {"label": _("Designation"), "fieldname": "designation", "fieldtype": "Link", "options": "Designation", "width": 150},
            {"label": _("Level"), "fieldname": "level", "fieldtype": "Data", "width": 100},
            {"label": _("Company"), "fieldname": "company", "fieldtype": "Link", "options": "Company", "width": 150},
            {"label": _("Gross Pay"), "fieldname": "gross_pay", "fieldtype": "Float", "width": 120},
            {"label": _("Nationality"), "fieldname": "nationality", "fieldtype": "Data", "width": 100},
            
            {"label": _("Increment"), "fieldname": "increment", "fieldtype": "Data", "width": 120},
            {"label": _("Promotion"), "fieldname": "promotion", "fieldtype": "Data", "width": 120},
            {"label": _("Medical Insurance / Month"), "fieldname": "medical_insurance", "fieldtype": "Float", "width": 150},
            {"label": _("No of Family"), "fieldname": "no_of_family", "fieldtype": "Int", "width": 100},
            {"label": _("Ticket"), "fieldname": "ticket", "fieldtype": "Float", "width": 120},
            {"label": _("Iqama Cost / Month"), "fieldname": "iqama_cost", "fieldtype": "Data", "width": 150},
            {"label": _("VISA"), "fieldname": "visa", "fieldtype": "Data", "width": 120},
            {"label": _("Training cost / month"), "fieldname": "training_cost", "fieldtype": "Data", "width": 150},
            {"label": _("Penalty"), "fieldname": "penalty", "fieldtype": "Data", "width": 120},
            {"label": _("EOS"), "fieldname": "eos", "fieldtype": "Data", "width": 120},
            {"label": _("Yearly Bonus / Month"), "fieldname": "yearly_bonus", "fieldtype": "Data", "width": 150},
            {"label": _("WHT"), "fieldname": "wht", "fieldtype": "Data", "width": 120},
            {"label": _("Total"), "fieldname": "total", "fieldtype": "Data", "width": 150}
        ]
    
    return columns


def get_data(filters):
    conditions = get_conditions(filters)
    
    employees = frappe.db.sql("""
        SELECT 
            emp.name,
            emp.employee_name,
            emp.department,
            emp.designation,
            d.custom_level,
            emp.company,
            (emp.custom_base + emp.custom_housing + emp.custom_transportation + emp.custom_other_allowance) AS 'gross_pay',
            emp.custom_base AS 'Basic',
            emp.custom_housing AS 'Housing',
            emp.nationality
        FROM 
            `tabEmployee` emp
        JOIN 
            `tabDesignation` d
        ON 
            d.name = emp.designation 
        WHERE 
            emp.status = 'Active'
            AND emp.employment_type = 'Permanent'
            {conditions}
        ORDER BY 
            emp.name
    """.format(conditions=conditions), filters, as_dict=1)
    
    data = []
    
    for emp in employees:
        row = get_employee_budget_data(emp, filters)
        data.append(row)
    
    return data


def get_employee_budget_data(emp, filters):
    
    no_of_family = get_employee_family_count(emp.name)

    monthly_medical = get_employee_monthly_medical(emp.name)
    
    row = {
        'employee': emp.name,
        'employee_name': emp.employee_name,
        'department': emp.department,
        'designation': emp.designation,
        'level': emp.custom_level,
        'company': emp.company,
        'gross_pay': emp.gross_pay,
        'no_of_family': no_of_family,
        'medical_insurance': monthly_medical,        
        'nationality' : emp.nationality
        
    }


    if filters.get("company") == "iValue KSA":
        row['basic'] = emp.Basic
        row['housing'] = emp.Housing

        if emp.nationality == 'Saudi':
            row['gosi'] = ((emp.Basic + emp.Housing) * 0.1175)
        else:            
            row['gosi'] = ((emp.Basic + emp.Housing) * 0.02)

        row['ticket'] = (no_of_family * 2000)
    
    elif filters.get("company") == "iValueJOR":
        row['social_security'] = (emp.gross_pay * 0.1425)
        row['ticket'] = (no_of_family * 377.35)

    elif filters.get("company") == "iValueUAE":
        row['ticket'] = (no_of_family * 2040.81)
  
    return row


def get_employee_family_count(employee):

    family_count = 1

    family_members = frappe.db.sql("""
        SELECT 
            name1,
            relation,
            date_of_birth
        FROM 
            `tabEmployee Family`
        WHERE 
            parent = %s AND parentfield = 'family'
    """, (employee), as_dict=1)

    for member in family_members:
        relation = member.get("relation")
        dob = member.get("date_of_birth")

        
        if isinstance(dob, str):
            dob = datetime.strptime(dob, "%Y-%m-%d").date()

        if relation in ["Husband", "Wife"]:
            family_count += 1

        elif relation in ["Son", "Daughter"] and dob:
            age = (date.today() - dob).days / 365.25
            if age < 18:
                family_count += 1
    
    return family_count


def get_employee_monthly_medical(employee):
    med = 0

    family_members = frappe.db.sql("""
        SELECT
            SUM(debit) AS total_debit
        FROM 
            `tabGL Entry`
        WHERE 
            docstatus = 1
            AND account LIKE '%%5229 - Medical and Insurance%%'
            AND remarks LIKE '%%Cost Distribution Account%%'
            AND posting_date BETWEEN '2025-08-01' AND '2025-08-31'
            AND party_type = 'Employee' 
            AND party = %s
    """, (employee), as_dict=1)

    if family_members and family_members[0].get("total_debit"):
        med = family_members[0]["total_debit"]

    return med


def get_conditions(filters):
    conditions = ""
    
    if filters.get("company"):
        conditions += " AND emp.company = %(company)s"

    return conditions


