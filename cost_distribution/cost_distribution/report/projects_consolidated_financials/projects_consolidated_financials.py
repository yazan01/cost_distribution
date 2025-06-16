from collections import OrderedDict
import frappe
from frappe import _, _dict

def execute(filters):
    columns = [
        {"label": "Project ID", "fieldname": "project_id", "fieldtype": "Link", "options": "Project", "width": 120},
        {"label": "Project Name A", "fieldname": "project_name_a", "fieldtype": "Data", "width": 250},
        {"label": "Project Name E", "fieldname": "project_name_e", "fieldtype": "Data", "width": 250},
        {"label": "Project Type", "fieldname": "project_type", "fieldtype": "Data", "width": 150},
        {"label": "Project Status", "fieldname": "project_status", "fieldtype": "Data", "width": 150},
        {"label": "Client", "fieldname": "client", "fieldtype": "Data", "width": 250},
        {"label": "Project Manager", "fieldname": "project_manager", "fieldtype": "Link", "options": "Employee", "width": 180},
        {"label": "Project Manager Name", "fieldname": "project_manager_name", "fieldtype": "Data", "width": 200},

        {"label": "Year 2023 CTC Cost", "fieldname": "ctc_2023", "fieldtype": "Float", "width": 150},
        {"label": "Year 2024 CTC Cost", "fieldname": "ctc_2024", "fieldtype": "Float", "width": 150},
        {"label": "Year 2025 CTC Cost", "fieldname": "ctc_2025", "fieldtype": "Float", "width": 150},
        {"label": "Total CTC Cost", "fieldname": "total_ctc", "fieldtype": "Float", "width": 150},

        {"label": "Year 2023 Actual Cost", "fieldname": "actual_2023", "fieldtype": "Float", "width": 150},
        {"label": "Year 2024 Actual Cost", "fieldname": "actual_2024", "fieldtype": "Float", "width": 150},
        {"label": "Year 2025 Actual Cost", "fieldname": "actual_2025", "fieldtype": "Float", "width": 150},
        {"label": "Total Actual Cost", "fieldname": "total_actual", "fieldtype": "Float", "width": 150},

        {"label": "Year 2023 Revenue", "fieldname": "revenue_2023", "fieldtype": "Float", "width": 150},
        {"label": "Year 2024 Revenue", "fieldname": "revenue_2024", "fieldtype": "Float", "width": 150},
        {"label": "Year 2025 Revenue", "fieldname": "revenue_2025", "fieldtype": "Float", "width": 150},
        {"label": "Total Revenue", "fieldname": "total_revenue", "fieldtype": "Float", "width": 150},

        {"label": "Profit AND Loss on CTC Cost", "fieldname": "profit_loss_ctc", "fieldtype": "Float", "width": 200},
        {"label": "Profit AND Loss on Actual Cost", "fieldname": "profit_loss_actual", "fieldtype": "Float", "width": 200},
    ]

    
    data = get_project_data(filters)
    return columns, data

def get_project_data(filters):
    project_filter = filters.get("project")
    partner_filter = filters.get("partner")
    project_type_filter = filters.get("project_type")

    project_status = filters.get("status")
    customer = filters.get("customer")
    
    with frappe.flags.in_permission_query_override:
        projects = frappe.db.sql("""
            SELECT 
                p.name AS project_id, 
                p.project_name AS project_name_a, 
                p.project_name_in_english AS project_name_e, 
                p.project_type AS project_type,
                p.status AS project_status,
                p.customer AS client,
                p.project_manager AS project_manager, 
                p.project_manager_name AS project_manager_name
            FROM `tabProject` p
            WHERE 
                (%(project_filter)s IS NULL OR p.name = %(project_filter)s)
                AND (%(partner_filter)s IS NULL OR p.project_manager = %(partner_filter)s)
                AND (%(project_type_filter)s IS NULL OR p.project_type = %(project_type_filter)s)
                AND (%(project_status)s IS NULL OR p.status = %(project_status)s)
                AND (%(customer)s IS NULL OR p.customer = %(customer)s)
        """, {
            "project_filter": project_filter,
            "partner_filter": partner_filter,
            "project_type_filter": project_type_filter,
            "project_status": project_status,
            "customer": customer
        }, as_dict=True)

    project_ids = [p["project_id"] for p in projects]
    if not project_ids:
        return []
    
    with frappe.flags.in_permission_query_override:
        financial_data = frappe.db.sql("""
            SELECT 
                gl.project AS project_id,
                YEAR(gl.posting_date) AS year,
                SUM(CASE WHEN gl.account LIKE %(act)s AND gl.company = 'iValueJOR' THEN gl.debit * 5.3 - gl.credit * 5.3 
                         WHEN gl.account LIKE %(act)s AND gl.company = 'iValueUAE' THEN gl.debit * 1.02 - gl.credit * 1.02 
                         WHEN gl.account LIKE %(act)s AND gl.company = 'iValue KSA' THEN gl.debit - gl.credit ELSE 0 END)
                -SUM(CASE WHEN gl.account LIKE %(rev)s AND gl.company != p.company AND gl.company = 'iValueJOR' THEN gl.credit * 5.3 - gl.debit * 5.3
                         WHEN gl.account LIKE %(rev)s AND gl.company != p.company AND gl.company = 'iValueUAE' THEN gl.credit * 1.02 - gl.debit * 1.02
                         WHEN gl.account LIKE %(rev)s AND gl.company != p.company AND gl.company = 'iValue KSA' THEN gl.credit - gl.debit ELSE 0 END)
                         AS actual_cost,
                SUM(CASE WHEN gl.account LIKE %(rev)s AND gl.company = p.company AND gl.company = 'iValueJOR' THEN gl.credit * 5.3 - gl.debit * 5.3
                         WHEN gl.account LIKE %(rev)s AND gl.company = p.company AND gl.company = 'iValueUAE' THEN gl.credit * 1.02 - gl.debit * 1.02
                         WHEN gl.account LIKE %(rev)s AND gl.company = p.company AND gl.company = 'iValue KSA' THEN gl.credit - gl.debit ELSE 0 END) AS revenue
            FROM `tabGL Entry` gl
            JOIN `tabProject` p ON gl.project = p.name
            WHERE 
                gl.project IN %(project_ids)s 
                AND YEAR(gl.posting_date) IN (2023, 2024, 2025)
                AND gl.docstatus = 1 AND gl.is_cancelled = 0 AND gl.remarks NOT REGEXP "CAPITALIZATION"
            GROUP BY gl.project, YEAR(gl.posting_date)
        """, {"project_ids": project_ids, 'act': '5%', 'rev': '4%'}, as_dict=True)
    
    with frappe.flags.in_permission_query_override:
        ctc_data = frappe.db.sql("""
            SELECT 
                S.project AS project_id,
                YEAR(D.posting_date) AS year,
                ROUND(SUM(S.total_cost_of_project), 2) AS ctc_cost
            FROM `tabProject Summary CTC` S
            JOIN `tabCTC Distribution` D ON S.parent = D.name
            WHERE 
                S.project IN %(project_ids)s 
                AND YEAR(D.posting_date) IN (2023, 2024, 2025)
            GROUP BY S.project, YEAR(D.posting_date)
        """, {"project_ids": project_ids}, as_dict=True)
    
    with frappe.flags.in_permission_query_override:
        indirect_costs = frappe.db.sql("""
            SELECT 
                gl.project AS project_id,
                YEAR(gl.posting_date) AS year,
                SUM((gl.debit - gl.credit) * afc.currency) AS indirect_cost
            FROM `tabAccounts For CTC` AS afc
            JOIN `tabGL Entry` AS gl ON afc.account = gl.account 
            WHERE 
                gl.project IN %(project_ids)s 
                AND YEAR(gl.posting_date) IN (2023, 2024, 2025)
                AND afc.type = 'Indirect' 
                AND gl.docstatus = 1 
                AND gl.is_cancelled = 0 
                AND gl.account LIKE %(acc)s
                AND gl.remarks NOT REGEXP "Cost Distribution" AND gl.remarks NOT REGEXP "CAPITALIZATION"
            GROUP BY gl.project, YEAR(gl.posting_date)
        """, {"project_ids": project_ids, 'acc': '5%'}, as_dict=True)

    # تحويل البيانات إلى قواميس للوصول السريع
    financial_dict = {(f["project_id"], f["year"]): f for f in financial_data}
    ctc_dict = {(c["project_id"], c["year"]): c["ctc_cost"] for c in ctc_data}
    indirect_cost_dict = {(t["project_id"], t["year"]): t["indirect_cost"] for t in indirect_costs}

    data = []
    for project in projects:
        project_id = project["project_id"]

        ctc_2023 = ctc_dict.get((project_id, 2023), 0)+indirect_cost_dict.get((project_id, 2023), 0)
        ctc_2024 = ctc_dict.get((project_id, 2024), 0)+indirect_cost_dict.get((project_id, 2024), 0)
        ctc_2025 = ctc_dict.get((project_id, 2025), 0)+indirect_cost_dict.get((project_id, 2025), 0)
        total_ctc = ctc_2023 + ctc_2024 + ctc_2025

        actual_2023 = financial_dict.get((project_id, 2023), {}).get("actual_cost", 0)
        actual_2024 = financial_dict.get((project_id, 2024), {}).get("actual_cost", 0)
        actual_2025 = financial_dict.get((project_id, 2025), {}).get("actual_cost", 0)
        total_actual = actual_2023 + actual_2024 + actual_2025

        revenue_2023 = financial_dict.get((project_id, 2023), {}).get("revenue", 0)
        revenue_2024 = financial_dict.get((project_id, 2024), {}).get("revenue", 0)
        revenue_2025 = financial_dict.get((project_id, 2025), {}).get("revenue", 0)
        total_revenue = revenue_2023 + revenue_2024 + revenue_2025

        row = {
            **project,
            "ctc_2023": ctc_2023, "ctc_2024": ctc_2024, "ctc_2025": ctc_2025, "total_ctc": total_ctc,
            "actual_2023": actual_2023, "actual_2024": actual_2024, "actual_2025": actual_2025, "total_actual": total_actual,
            "revenue_2023": revenue_2023, "revenue_2024": revenue_2024, "revenue_2025": revenue_2025, "total_revenue": total_revenue,
            "profit_loss_ctc": total_revenue - total_ctc,
            "profit_loss_actual": total_revenue - total_actual
        }
        data.append(row)

    return data

@frappe.whitelist()
def get_partner_list():
    return frappe.get_all(
        "Employee",
        filters={"designation": ["in", ["Partner", "CEO"]]},
        fields=["name", "employee_name"],
        ignore_permissions=True
    )
