from collections import OrderedDict
import frappe
from frappe import _, _dict

def execute(filters):
    columns = [
        {"label": "Project ID", "fieldname": "project_id", "fieldtype": "Link", "options": "Project", "width": 120},
        {"label": "Percentage", "fieldname": "percentage", "fieldtype": "Percent", "width": 120},
        {"label": "Project Name A", "fieldname": "project_name_a", "fieldtype": "Data", "width": 250},
        {"label": "Project Name E", "fieldname": "project_name_e", "fieldtype": "Data", "width": 250},
        {"label": "Project Type", "fieldname": "project_type", "fieldtype": "Data", "width": 150},
        {"label": "Project Status", "fieldname": "project_status", "fieldtype": "Data", "width": 150},
        {"label": "Client", "fieldname": "client", "fieldtype": "Data", "width": 250},

        {"label": "Date", "fieldname": "date", "fieldtype": "Date", "width": 150},
        {"label": "Company", "fieldname": "company", "fieldtype": "Data", "width": 150},
        {"label": "Account", "fieldname": "account", "fieldtype": "Data", "width": 300},
        {"label": "Voucher Type", "fieldname": "voucher_type", "fieldtype": "Data", "width": 150},
        {"label": "Voucher No", "fieldname": "voucher_no", "fieldtype": "Data", "width": 150},

        {"label": "Party Type", "fieldname": "party_type", "fieldtype": "Data", "width": 150},
        {"label": "Party", "fieldname": "party", "fieldtype": "Data", "width": 200},
        {"label": "Description", "fieldname": "description", "fieldtype": "Data", "width": 300},      

        {"label": "Debit", "fieldname": "debit", "fieldtype": "Float", "width": 150},
        {"label": "Credit", "fieldname": "credit", "fieldtype": "Float", "width": 150},
        {"label": "Balance", "fieldname": "balance", "fieldtype": "Float", "width": 150},


    ]

    data = get_project_data(filters)
    return columns, data

def get_project_data(filters):
    project_filter = filters.get("project")
    partner_filter = filters.get("partner")
    project_type_filter = filters.get("project_type")
    portfolio_category_filter = filters.get("portfolio_category")
    from_date_filter = filters.get("from_date")
    to_date_filter = filters.get("to_date")
    aggregated_filter = filters.get("aggregated")
    data_type = filters.get("data_type")

    if project_filter:
        if isinstance(project_filter, list):
            project_filter_tuple = tuple(project_filter)
        else:
            project_filter_tuple = (project_filter,)
    else:
        project_filter_tuple = ()

    where_clauses = ["pp.partner = %(partner_filter)s"]
    if project_filter_tuple:
        where_clauses.append("pp.parent IN %(project_filter)s")
    if project_type_filter:
        where_clauses.append("pro.project_type = %(project_type_filter)s")
    if portfolio_category_filter:
        where_clauses.append("pro.custom_portfolio_category = %(portfolio_category_filter)s")

    where_sql = " AND ".join(where_clauses)

    params = {
        "partner_filter": partner_filter,
        "project_filter": project_filter_tuple,
        "project_type_filter": project_type_filter,
        "portfolio_category_filter": portfolio_category_filter,
        "from_date": from_date_filter,
        "to_date": to_date_filter,
        "act": "5%",
        "rev": "4%",
        "acc": "5%",
    }

    all_projects = frappe.db.sql(f"""
        SELECT 
            pp.parent AS project_id,
            pp.percentage AS percentage,
            pro.project_name AS project_name_a, 
            pro.project_name_in_english AS project_name_e, 
            pro.project_type AS project_type,
            pro.status AS project_status,
            pro.customer AS client
        FROM `tabPartners Percentage` pp
        JOIN `tabProject` pro ON pro.name = pp.parent
        WHERE {where_sql}
    """, params, as_dict=True)

    project_percentages = {p["project_id"]: float(p["percentage"] or 0) / 100 for p in all_projects}
    project_ids = list(project_percentages.keys())

    if not project_ids:
        return []

    date_condition = ""
    if from_date_filter and to_date_filter:
        date_condition = "AND gl.posting_date BETWEEN %(from_date)s AND %(to_date)s"
    elif from_date_filter:
        date_condition = "AND gl.posting_date >= %(from_date)s"
    elif to_date_filter:
        date_condition = "AND gl.posting_date <= %(to_date)s"

    date_condition_ctc = ""
    if from_date_filter and to_date_filter:
        date_condition_ctc = "AND D.posting_date BETWEEN %(from_date)s AND %(to_date)s"
    elif from_date_filter:
        date_condition_ctc = "AND D.posting_date >= %(from_date)s"
    elif to_date_filter:
        date_condition_ctc = "AND D.posting_date <= %(to_date)s"


    # Based on the data type, fetch the appropriate records
    
    if data_type == "CTC":
        # CTC Cost data
        ctc_entries = get_ctc_entries(params, project_ids, date_condition_ctc)
        indirect_entries = get_indirect_cost_entries(params, project_ids, date_condition)
        data = ctc_entries + indirect_entries
    
    elif data_type == "Actual Cost":
        # Actual Cost data
        actual_cost = get_actual_cost_entries(params, project_ids, date_condition)
        revenue_other_company = get_revenue_entries_other_company(params, project_ids, date_condition)
        data = actual_cost + revenue_other_company
    
    elif data_type == "Revenue":
        # Revenue data
        data = get_revenue_entries(params, project_ids, date_condition)
    
    elif data_type == "Profit Loss CTC":
        # Profit/Loss on CTC
        revenue_data = get_revenue_entries(params, project_ids, date_condition)
        ctc_entries = get_ctc_entries(params, project_ids, date_condition_ctc)
        indirect_entries = get_indirect_cost_entries(params, project_ids, date_condition)
        data = revenue_data + ctc_entries + indirect_entries
    
    elif data_type == "Profit Loss Actual":
        # Profit/Loss on Actual Cost
        revenue_data = get_revenue_entries(params, project_ids, date_condition)
        actual_data = get_actual_cost_entries(params, project_ids, date_condition)
        revenue_other_company = get_revenue_entries_other_company(params, project_ids, date_condition)
        data = revenue_data + actual_data + revenue_other_company
    
    # Sort the data by date
    data.sort(key=lambda x: x.get("posting_date"))
    
    final_data = []

    for entry in data:
        project_id = entry.get("project")

        if not project_id or project_id not in project_percentages:
            continue  # تجاهل الإدخالات التي لا تتبع مشاريعنا المحددة

        # البحث عن بيانات المشروع
        project_info = next((p for p in all_projects if p["project_id"] == project_id), {})

        # إنشاء سجل جديد يحتوي على جميع البيانات
        final_data.append({
            "project_id": project_info.get("project_id"),
            "percentage": project_info.get("percentage"),
            "project_name_a": project_info.get("project_name_a"),
            "project_name_e": project_info.get("project_name_e"),
            "project_type": project_info.get("project_type"),
            "project_status": project_info.get("project_status"),
            "client": project_info.get("client"),

            "date": entry.get("posting_date"),
            "company": entry.get("company"),
            "account": entry.get("account"),
            "voucher_type": entry.get("voucher_type"),
            "voucher_no": entry.get("voucher_no"),

            "party_type": entry.get("party_type"),
            "party": entry.get("party"),
            "description": entry.get("remarks"),

            "debit": entry.get("debit", 0),
            "credit": entry.get("credit", 0),
            "balance": entry.get("credit", 0) - entry.get("debit", 0)
        })

    return final_data

    


def get_ctc_entries(params, project_ids, date_condition_ctc):
    """Get CTC cost distribution entries for the specified project and date range"""
    
    entries = frappe.db.sql(f"""
        SELECT 
            D.project,
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
            S.project IN %(project_ids)s {date_condition_ctc}     
    """, {**params, "project_ids": project_ids}, as_dict=True)
    
    return entries

def get_indirect_cost_entries(params, project_ids, date_condition):
    """Get indirect cost entries for the specified project and date range"""
    
    entries = frappe.db.sql(f"""
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
            gl.debit * afc.currency AS debit,
            gl.credit * afc.currency AS credit
        FROM `tabAccounts For CTC` AS afc
        JOIN `tabGL Entry` AS gl ON afc.account = gl.account 
        WHERE 
            gl.project IN %(project_ids)s
            AND afc.type = 'Indirect'
            AND gl.docstatus = 1 
            AND gl.is_cancelled = 0
            AND gl.account LIKE %(acc)s
            AND gl.remarks NOT REGEXP "Cost Distribution"
            {date_condition}
        ORDER BY gl.posting_date
    """, {**params, "project_ids": project_ids}, as_dict=True)
    
    return entries

def get_actual_cost_entries(params, project_ids, date_condition):
    """Get actual cost entries for the specified project and date range"""
    
    entries = frappe.db.sql(f"""
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
                WHEN gl.company = 'iValueJOR' THEN gl.debit * 5.3 
                WHEN gl.company = 'iValueUAE' THEN gl.debit * 1.02
                ELSE gl.debit
            END AS debit,
            CASE 
                WHEN gl.company = 'iValueJOR' THEN gl.credit * 5.3
                WHEN gl.company = 'iValueUAE' THEN gl.credit * 1.02
                ELSE gl.credit
            END AS credit
        FROM `tabGL Entry` gl
        JOIN `tabProject` p ON gl.project = p.name
        WHERE 
            gl.project IN %(project_ids)s
            AND gl.docstatus = 1 
            AND gl.is_cancelled = 0 
            AND gl.account LIKE %(act)s
            {date_condition}
        ORDER BY gl.posting_date
    """, {**params, "project_ids": project_ids}, as_dict=True)
    
    return entries

def get_revenue_entries_other_company(params, project_ids, date_condition):
    """Get revenue entries for the specified project and date range"""
    
    entries = frappe.db.sql(f"""
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
                WHEN gl.company = 'iValueJOR' THEN gl.debit * 5.3
                WHEN gl.company = 'iValueUAE' THEN gl.debit * 1.02
                ELSE gl.debit
            END AS debit,
            CASE 
                WHEN gl.company = 'iValueJOR' THEN gl.credit * 5.3
                WHEN gl.company = 'iValueUAE' THEN gl.credit * 1.02
                ELSE gl.credit
            END AS credit
        FROM `tabGL Entry` gl
        JOIN `tabProject` p ON gl.project = p.name
        WHERE 
            gl.project IN %(project_ids)s
            AND gl.docstatus = 1 
            AND gl.is_cancelled = 0 
            AND gl.account LIKE %(rev)s
            AND gl.company != p.company
            {date_condition}
        ORDER BY gl.posting_date
    """, {**params, "project_ids": project_ids}, as_dict=True)
    
    return entries


def get_revenue_entries(params, project_ids, date_condition):
    """Get revenue entries for the specified project and date range"""
    
    entries = frappe.db.sql(f"""
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
                WHEN gl.company = 'iValueJOR' THEN gl.debit * 5.3
                WHEN gl.company = 'iValueUAE' THEN gl.debit * 1.02
                ELSE gl.debit
            END AS debit,
            CASE 
                WHEN gl.company = 'iValueJOR' THEN gl.credit * 5.3
                WHEN gl.company = 'iValueUAE' THEN gl.credit * 1.02
                ELSE gl.credit
            END AS credit
        FROM `tabGL Entry` gl
        JOIN `tabProject` p ON gl.project = p.name
        WHERE 
            gl.project IN %(project_ids)s
            AND gl.docstatus = 1 
            AND gl.is_cancelled = 0 
            AND gl.account LIKE %(rev)s
            AND gl.company = p.company
        ORDER BY gl.posting_date
    """, {**params, "project_ids": project_ids}, as_dict=True)
    
    return entries



@frappe.whitelist()
def get_projects_by_partner(partner, txt="", project_type=None, portfolio_category=None):
    # نبني شروط WHERE ديناميكيًا
    where_clauses = ["pp.partner = %(partner)s"]

    if project_type:
        where_clauses.append("pro.project_type = %(project_type)s")
    if portfolio_category:
        where_clauses.append("pro.custom_portfolio_category = %(portfolio_category)s")
    if txt:
        where_clauses.append("pro.name LIKE %(txt)s")

    where_sql = " AND ".join(where_clauses)

    query = f"""
        SELECT 
            pp.parent AS project
        FROM 
            `tabPartners Percentage` pp
        JOIN 
            `tabProject` pro ON pro.name = pp.parent
        WHERE 
            {where_sql}
    """

    results = frappe.db.sql(query, {
        "partner": partner,
        "project_type": project_type,
        "portfolio_category": portfolio_category,
        "txt": f"%{txt}%" if txt else None
    }, as_dict=True)

    # إرجاع القائمة بصيغة MultiSelectList
    return [{"value": row.project, "description": row.project} for row in results]
