from collections import OrderedDict
import frappe
from frappe import _, _dict
from datetime import datetime, date

def execute(filters):
    if not filters or not filters.get("project"):
        return [], []
    
    project_id = filters.get("project")
    data_type = filters.get("data_type")
    from_date = filters.get("from_date")
    to_date = filters.get("to_date")

    
    # Configure the columns for the detail report
    columns = [
        {"label": "Date", "fieldname": "posting_date", "fieldtype": "Date", "width": 120},
        {"label": "Company", "fieldname": "company", "fieldtype": "Link", "options": "Company", "width": 120},
        {"label": "Account", "fieldname": "account", "fieldtype": "Link", "options": "Account", "width": 250},
        {"label": "Voucher Type", "fieldname": "voucher_type", "fieldtype": "Data", "width": 150},
        {"label": "Voucher No", "fieldname": "voucher_no", "fieldtype": "Dynamic Link", "options": "voucher_type", "width": 250},
        {"label": "Party Type", "fieldname": "party_type", "fieldtype": "Data", "width": 120},
        {"label": "Party", "fieldname": "party", "fieldtype": "Data", "width": 300},
        {"label": "Description", "fieldname": "remarks", "fieldtype": "Data", "width": 300},
        {"label": "Debit", "fieldname": "debit", "fieldtype": "Currency", "width": 150},
        {"label": "Credit", "fieldname": "credit", "fieldtype": "Currency", "width": 150},
        {"label": "Total", "fieldname": "total", "fieldtype": "Currency", "width": 150}
    ]
    
    # Get the data for the report
    data = get_detail_data(project_id, data_type, from_date, to_date)
    
   
    return columns, data

def get_detail_data(project_id, data_type, from_date, to_date):
    """Get detailed data based on the project ID and data type within date range"""
    
    # Fetch project information for validation
    project = frappe.get_doc("Project", project_id)
    if not project:
        return []
    
    data = []
    
    # Based on the data type, fetch the appropriate records
    if data_type == "CTC":
        # CTC Cost data
        ctc_entries = get_ctc_entries(project_id, from_date, to_date)
        indirect_entries = get_indirect_cost_entries(project_id, from_date, to_date)
        data = ctc_entries + indirect_entries
    
    elif data_type == "Actual Cost":
        # Actual Cost data
        actual_cost = get_actual_cost_entries(project_id, from_date, to_date)
        revenue_other_company = get_revenue_entries_other_company(project_id, from_date, to_date)
        data = actual_cost + revenue_other_company
    
    elif data_type == "Revenue":
        # Revenue data
        data = get_revenue_entries(project_id, from_date, to_date)
    
    elif data_type == "Profit Loss CTC":
        # Profit/Loss on CTC
        revenue_data = get_revenue_entries(project_id, from_date, to_date)
        ctc_entries = get_ctc_entries(project_id, from_date, to_date)
        indirect_entries = get_indirect_cost_entries(project_id, from_date, to_date)
        data = revenue_data + ctc_entries + indirect_entries
    
    elif data_type == "Profit Loss Actual":
        # Profit/Loss on Actual Cost
        revenue_data = get_revenue_entries(project_id, from_date, to_date)
        actual_data = get_actual_cost_entries(project_id, from_date, to_date)
        revenue_other_company = get_revenue_entries_other_company(project_id, from_date, to_date)
        data = revenue_data + actual_data + revenue_other_company
    
    # Sort the data by date
    data.sort(key=lambda x: x.get("posting_date"))
    
    # Calculate the running balance
    
    for entry in data:
        debit = entry.get("debit", 0)
        credit = entry.get("credit", 0)
        
        entry["total"] = credit - debit    
    return data

def get_ctc_entries(project_id, from_date, to_date):
    """Get CTC cost distribution entries for the specified project and date range"""
    
    entries = frappe.db.sql("""
        SELECT 
            D.posting_date,
            D.company,
            'CTC Distribution' AS account,
            'CTC Distribution' AS voucher_type,
            D.name AS voucher_no,
            'Employee' AS party_type,
            CONCAT(S.employee, ' : ', (SELECT employee_name FROM `tabEmployee` WHERE name = S.employee)) AS party,
            CONCAT('CTC Cost for ', E.employee_name) AS remarks,
            S.total_cost_of_project AS debit,
            0 AS credit
        FROM `tabProject Summary CTC` S
        JOIN `tabCTC Distribution` D ON S.parent = D.name
        JOIN `tabEmployee` E ON S.employee = E.name
        WHERE 
            S.project = %s
            AND D.posting_date BETWEEN %s AND %s        
    """, (project_id, from_date, to_date), as_dict=True)
    
    return entries

def get_indirect_cost_entries(project_id, from_date, to_date):
    """Get indirect cost entries for the specified project and date range"""
    
    entries = frappe.db.sql("""
        SELECT 
            gl.posting_date,
            gl.company,
            gl.account,
            gl.voucher_type,
            gl.voucher_no,
            gl.party_type AS party_type,
            CASE 
                WHEN gl.party_type = 'Employee' THEN 
                    CONCAT(gl.party, ' : ', (SELECT employee_name FROM `tabEmployee` WHERE name = gl.party))
                ELSE gl.party 
            END AS party,
            gl.remarks,
            gl.debit * afc.currency - gl.credit * afc.currency AS debit,
            0 AS credit
        FROM `tabAccounts For CTC` AS afc
        JOIN `tabGL Entry` AS gl ON afc.account = gl.account 
        WHERE 
            gl.project = %s
            AND gl.posting_date BETWEEN %s AND %s
            AND afc.type = 'Indirect' 
            AND gl.docstatus = 1 
            AND gl.is_cancelled = 0 
            AND gl.account LIKE %s
            AND gl.remarks NOT REGEXP "Cost Distribution"
        ORDER BY gl.posting_date
    """, (project_id, from_date, to_date, "5%"), as_dict=True)
    
    return entries

def get_actual_cost_entries(project_id, from_date, to_date):
    """Get actual cost entries for the specified project and date range"""
    
    entries = frappe.db.sql("""
        SELECT 
            gl.posting_date,
            gl.company,
            gl.account,
            gl.voucher_type,
            gl.voucher_no,
            gl.party_type AS party_type,
            CASE 
                WHEN gl.party_type = 'Employee' THEN 
                    CONCAT(gl.party, ' : ', (SELECT employee_name FROM `tabEmployee` WHERE name = gl.party))
                ELSE gl.party 
            END AS party,
            gl.remarks,
            CASE 
                WHEN gl.company = 'iValueJOR' THEN gl.debit * 5.3 - gl.credit * 5.3
                WHEN gl.company = 'iValueUAE' THEN gl.debit * 1.02 - gl.credit * 1.02
                ELSE gl.debit - gl.credit
            END AS debit,
            0 AS credit
        FROM `tabGL Entry` gl
        JOIN `tabProject` p ON gl.project = p.name
        WHERE 
            gl.project = %s
            AND gl.posting_date BETWEEN %s AND %s
            AND gl.docstatus = 1 
            AND gl.is_cancelled = 0 
            AND gl.account LIKE %s
        ORDER BY gl.posting_date
    """, (project_id, from_date, to_date, "5%"), as_dict=True)
    
    return entries

def get_revenue_entries_other_company(project_id, from_date, to_date):
    """Get revenue entries for the specified project and date range"""
    
    entries = frappe.db.sql("""
        SELECT 
            gl.posting_date,
            gl.company,
            gl.account,
            gl.voucher_type,
            gl.voucher_no,
            gl.party_type AS party_type,
            CASE 
                WHEN gl.party_type = 'Employee' THEN 
                    CONCAT(gl.party, ' : ', (SELECT employee_name FROM `tabEmployee` WHERE name = gl.party))
                ELSE gl.party 
            END AS party,
            gl.remarks,
            CASE 
                WHEN gl.company = 'iValueJOR' THEN gl.debit * 5.3 - gl.credit * 5.3
                WHEN gl.company = 'iValueUAE' THEN gl.debit * 1.02 - gl.credit * 1.02
                ELSE gl.debit - gl.credit
            END AS debit,
            0 AS credit
        FROM `tabGL Entry` gl
        JOIN `tabProject` p ON gl.project = p.name
        WHERE 
            gl.project = %s
            AND gl.posting_date BETWEEN %s AND %s
            AND gl.docstatus = 1 
            AND gl.is_cancelled = 0 
            AND gl.account LIKE %s
            AND gl.company != p.company
        ORDER BY gl.posting_date
    """, (project_id, from_date, to_date, "4%"), as_dict=True)
    
    return entries


def get_revenue_entries(project_id, from_date, to_date):
    """Get revenue entries for the specified project and date range"""
    
    entries = frappe.db.sql("""
        SELECT 
            gl.posting_date,
            gl.company,
            gl.account,
            gl.voucher_type,
            gl.voucher_no,
            gl.party_type AS party_type,
            CASE 
                WHEN gl.party_type = 'Employee' THEN 
                    CONCAT(gl.party, ' : ', (SELECT employee_name FROM `tabEmployee` WHERE name = gl.party))
                ELSE gl.party 
            END AS party,
            gl.remarks,
            0 AS debit,
            CASE 
                WHEN gl.company = 'iValueJOR' THEN gl.credit * 5.3 - gl.debit * 5.3
                WHEN gl.company = 'iValueUAE' THEN gl.credit * 1.02 - gl.debit * 1.02
                ELSE gl.credit - gl.debit
            END AS credit
        FROM `tabGL Entry` gl
        JOIN `tabProject` p ON gl.project = p.name
        WHERE 
            gl.project = %s
            AND gl.posting_date BETWEEN %s AND %s
            AND gl.docstatus = 1 
            AND gl.is_cancelled = 0 
            AND gl.account LIKE %s
            AND gl.company = p.company
        ORDER BY gl.posting_date
    """, (project_id, from_date, to_date, "4%"), as_dict=True)
    
    return entries