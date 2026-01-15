from collections import OrderedDict
import frappe
from frappe import _, _dict
import json

def execute(filters):
    columns = [
        {"label": "Project ID", "fieldname": "project_id", "fieldtype": "Link", "options": "Project", "width": 120},
        {"label": "Percentage", "fieldname": "percentage", "fieldtype": "Percent", "width": 120},
        {"label": "Project Name A", "fieldname": "project_name_a", "fieldtype": "Data", "width": 250},
        {"label": "Project Name E", "fieldname": "project_name_e", "fieldtype": "Data", "width": 250},
        {"label": "Project Type", "fieldname": "project_type", "fieldtype": "Data", "width": 150},
        {"label": "Project Status", "fieldname": "project_status", "fieldtype": "Data", "width": 150},
        {"label": "Client", "fieldname": "client", "fieldtype": "Data", "width": 250},
        {"label": "Sales Order Amount", "fieldname": "sales_order_amount", "fieldtype": "Float", "width": 200},
        {"label": "CTC Cost", "fieldname": "total_ctc", "fieldtype": "Float", "width": 200},
        {"label": "Revenue", "fieldname": "total_revenue", "fieldtype": "Float", "width": 200},
        {"label": "Profit AND Loss on CTC Cost", "fieldname": "profit_loss_ctc", "fieldtype": "Float", "width": 240},
    ]

    data = get_project_data(filters)

    add_total_row = 0 if filters.get("aggregated") else 1
    return columns, data, add_total_row

def get_project_data(filters):
    project_filter = filters.get("project")
    partner_filter = filters.get("partner")
    project_type_filter = filters.get("project_type")
    portfolio_category_filter = filters.get("portfolio_category")
    from_date_filter = filters.get("from_date")
    to_date_filter = filters.get("to_date")
    aggregated_filter = filters.get("aggregated")
    persentage_f = filters.get("persentage")

    if project_filter:
        if isinstance(project_filter, list):
            project_filter_tuple = tuple(project_filter)
        else:
            project_filter_tuple = (project_filter,)
    else:
        project_filter_tuple = ()

    # Handle multi-select project_type
    project_type_tuple = ()
    if project_type_filter:
        if isinstance(project_type_filter, str) and project_type_filter.startswith('['):
            try:
                project_type_filter = json.loads(project_type_filter)
            except:
                pass
        
        if isinstance(project_type_filter, str):
            project_type_list = [pt.strip() for pt in project_type_filter.split(',') if pt.strip()]
        elif isinstance(project_type_filter, list):
            project_type_list = project_type_filter
        else:
            project_type_list = [project_type_filter]
        if project_type_list:
            project_type_tuple = tuple(project_type_list)

    # Handle multi-select portfolio_category
    portfolio_category_tuple = ()
    if portfolio_category_filter:
        if isinstance(portfolio_category_filter, str) and portfolio_category_filter.startswith('['):
            try:
                portfolio_category_filter = json.loads(portfolio_category_filter)
            except:
                pass
        
        if isinstance(portfolio_category_filter, str):
            portfolio_category_list = [pc.strip() for pc in portfolio_category_filter.split(',') if pc.strip()]
        elif isinstance(portfolio_category_filter, list):
            portfolio_category_list = portfolio_category_filter
        else:
            portfolio_category_list = [portfolio_category_filter]
        if portfolio_category_list:
            portfolio_category_tuple = tuple(portfolio_category_list)

    # Build where clauses dynamically
    where_clauses = ["pp.partner = %(partner_filter)s"]
    params = {
        "partner_filter": partner_filter,
        "from_date": from_date_filter,
        "to_date": to_date_filter,
        "act": "5%",
        "rev": "4%",
        "acc": "5%",
    }

    if project_filter_tuple:
        where_clauses.append("pp.parent IN %(project_filter)s")
        params["project_filter"] = project_filter_tuple
        
    if project_type_tuple:
        where_clauses.append("pro.project_type IN %(project_type_filter)s")
        params["project_type_filter"] = project_type_tuple
        
    if portfolio_category_tuple:
        where_clauses.append("pro.custom_portfolio_category IN %(portfolio_category_filter)s")
        params["portfolio_category_filter"] = portfolio_category_tuple

    where_sql = " AND ".join(where_clauses)

    all_projects = frappe.db.sql(f"""
        SELECT 
            pp.parent AS project_id,
            pp.percentage AS percentage,
            pro.project_name AS project_name_a, 
            pro.project_name_in_english AS project_name_e, 
            pro.project_type AS project_type,
            pro.status AS project_status,
            pro.customer AS client,
            so.total AS sales_order_amount
        FROM `tabPartners Percentage` pp
        JOIN `tabProject` pro ON pro.name = pp.parent
        LEFT JOIN `tabSales Order` so ON so.project = pro.name
        WHERE {where_sql}
    """, params, as_dict=True)

    if persentage_f:
        project_percentages = {p["project_id"]: float(p["percentage"] or 0) / 100 for p in all_projects}
    else:
        project_percentages = {p["project_id"]: float(100) / 100 for p in all_projects}
    
    project_ids = list(project_percentages.keys())

    if not project_ids:
        return []

    #update
    projects_exp = frappe.db.sql("SELECT name FROM `tabProject Accounts For CTC`", as_list=True)
    projects_list_exp_1 = [project[0] for project in projects_exp]

    projects_list_notexp = list(
        set(project_ids) - set(projects_list_exp_1)
    )
    projects_list_exp = list(
        set(projects_list_exp_1) & set(project_ids)
    )

    date_condition = ""
    if from_date_filter and to_date_filter:
        date_condition = "AND gl.posting_date BETWEEN %(from_date)s AND %(to_date)s"
    elif from_date_filter:
        date_condition = "AND gl.posting_date >= %(from_date)s"
    elif to_date_filter:
        date_condition = "AND gl.posting_date <= %(to_date)s"

    financial_data = frappe.db.sql(f"""
        SELECT 
            gl.project AS project_id,
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
        WHERE gl.project IN %(project_ids)s AND gl.docstatus = 1 AND gl.is_cancelled = 0 AND gl.remarks NOT REGEXP "CAPITALIZATION" {date_condition}
        GROUP BY gl.project
    """, {**params, "project_ids": project_ids}, as_dict=True)

    date_condition_ctc = ""
    if from_date_filter and to_date_filter:
        date_condition_ctc = "AND D.posting_date BETWEEN %(from_date)s AND %(to_date)s"
    elif from_date_filter:
        date_condition_ctc = "AND D.posting_date >= %(from_date)s"
    elif to_date_filter:
        date_condition_ctc = "AND D.posting_date <= %(to_date)s"

    ctc_data = frappe.db.sql(f"""
        SELECT 
            S.project AS project_id,
            ROUND(SUM(S.total_cost_of_project), 2) AS ctc_cost
        FROM `tabProject Summary CTC` S
        JOIN `tabCTC Distribution` D ON S.parent = D.name
        WHERE S.project IN %(project_ids)s {date_condition_ctc}
        GROUP BY S.project
    """, {**params, "project_ids": project_ids}, as_dict=True)

    indirect_data = []
    if projects_list_notexp:
        indirect_data = frappe.db.sql(f"""
            SELECT 
                gl.project AS project_id,
                SUM((gl.debit - gl.credit) * afc.currency) AS indirect_cost
            FROM `tabAccounts For CTC` afc
            JOIN `tabGL Entry` gl ON afc.account = gl.account
            WHERE 
                gl.project IN %(project_ids)s
                AND afc.type = 'Indirect'
                AND gl.docstatus = 1 
                AND gl.is_cancelled = 0
                AND gl.account LIKE %(acc)s
                AND gl.remarks NOT REGEXP "Cost Distribution POP" AND gl.remarks NOT REGEXP "CAPITALIZATION"
                {date_condition}
            GROUP BY gl.project
        """, {**params, "project_ids": projects_list_notexp}, as_dict=True)

    indirect_data_exp = []
    if projects_list_exp:
        indirect_data_exp = frappe.db.sql(f"""
            SELECT 
                gl.project AS project_id,
                SUM((gl.debit - gl.credit) * afc.currency) AS indirect_cost
            FROM `tabAccount VS Year CTC` AS avyc
            JOIN `tabAccounts For CTC` AS afc ON avyc.account_for_ctc = afc.account
            JOIN `tabGL Entry` AS gl ON gl.account = afc.account
            WHERE 
                gl.project IN %(project_ids)s
                AND avyc.parent = gl.project
                AND afc.type = 'Indirect'
                AND gl.docstatus = 1 
                AND gl.is_cancelled = 0
                AND YEAR(gl.posting_date) = avyc.year
                AND gl.account LIKE %(acc)s
                AND gl.remarks NOT REGEXP "Cost Distribution POP" AND gl.remarks NOT REGEXP "CAPITALIZATION"
                {date_condition}
            GROUP BY gl.project
        """, {**params, "project_ids": projects_list_exp}, as_dict=True)

    financial_lookup = {d["project_id"]: d for d in financial_data}
    ctc_lookup = {d["project_id"]: d["ctc_cost"] for d in ctc_data}
    indirect_lookup = {d["project_id"]: d["indirect_cost"] for d in indirect_data}
    indirect_lookup_exp = {d["project_id"]: d["indirect_cost"] for d in indirect_data_exp}

    final_data = []

    cumulative_ctc = cumulative_actual = cumulative_revenue = cumulative_pl_ctc = cumulative_pl_actual = 0
    t_total_ctc = t_total_revenue = 0.0
    
    for project in all_projects:
        pid = project.project_id
        percentage = project_percentages.get(pid, 0)

        ctc_cost = ctc_lookup.get(pid, 0.0)
        indirect_cost = indirect_lookup.get(pid, 0.0)
        indirect_costs_exp_val = indirect_lookup_exp.get(pid, 0.0)
        total_ctc = (ctc_cost + indirect_cost + indirect_costs_exp_val) * percentage

        actual = financial_lookup.get(pid, {}).get("actual_cost", 0.0) * percentage
        revenue = financial_lookup.get(pid, {}).get("revenue", 0.0) * percentage

        profit_loss_ctc = revenue - total_ctc
        profit_loss_actual = revenue - actual
        
        #//////
        t_total_ctc += total_ctc
        t_total_revenue += revenue
        
        if aggregated_filter:
            cumulative_ctc += total_ctc
            cumulative_actual += actual
            cumulative_revenue += revenue
            cumulative_pl_ctc += profit_loss_ctc
            cumulative_pl_actual += profit_loss_actual

            total_ctc = cumulative_ctc
            actual = cumulative_actual
            revenue = cumulative_revenue
            profit_loss_ctc = cumulative_pl_ctc
            profit_loss_actual = cumulative_pl_actual

        row = {
            "project_id": pid,
            "percentage": round(percentage * 100, 2),
            "project_name_a": project.project_name_a,
            "project_name_e": project.project_name_e,
            "project_type": project.project_type,
            "project_status": project.project_status,
            "client": project.client,
            "sales_order_amount": round(((project.sales_order_amount or 0.0) * percentage), 2),
            "total_ctc": round(total_ctc, 2),
            "total_actual": round(actual, 2),
            "total_revenue": round(revenue, 2),
            "profit_loss_ctc": round(profit_loss_ctc, 2),
            "profit_loss_actual": round(profit_loss_actual, 2),
        }

        final_data.append(row)

    total = {
        "client": "Total",
        "total_ctc": t_total_ctc,
        "total_revenue": t_total_revenue,
        "profit_loss_ctc": t_total_revenue - t_total_ctc
    }
    final_data.append(total)
    
    return final_data


@frappe.whitelist()
def get_projects_by_partner(partner, txt="", project_type=None, portfolio_category=None):
    import json
    
    # Parse partner if it's a JSON string
    if isinstance(partner, str) and partner.startswith('['):
        try:
            partner = json.loads(partner)[0] if json.loads(partner) else partner
        except:
            pass
    
    # Handle multi-select project_type
    project_type_tuple = ()
    if project_type:
        if isinstance(project_type, str) and project_type.startswith('['):
            try:
                project_type = json.loads(project_type)
            except:
                pass
        
        if isinstance(project_type, str):
            project_type_list = [pt.strip() for pt in project_type.split(',') if pt.strip()]
        elif isinstance(project_type, list):
            project_type_list = project_type
        else:
            project_type_list = [project_type]
        if project_type_list:
            project_type_tuple = tuple(project_type_list)

    # Handle multi-select portfolio_category
    portfolio_category_tuple = ()
    if portfolio_category:
        if isinstance(portfolio_category, str) and portfolio_category.startswith('['):
            try:
                portfolio_category = json.loads(portfolio_category)
            except:
                pass
        
        if isinstance(portfolio_category, str):
            portfolio_category_list = [pc.strip() for pc in portfolio_category.split(',') if pc.strip()]
        elif isinstance(portfolio_category, list):
            portfolio_category_list = portfolio_category
        else:
            portfolio_category_list = [portfolio_category]
        if portfolio_category_list:
            portfolio_category_tuple = tuple(portfolio_category_list)

    # Build where clauses dynamically
    where_clauses = ["pp.partner = %(partner)s"]
    params = {"partner": partner}

    if project_type_tuple:
        where_clauses.append("pro.project_type IN %(project_type)s")
        params["project_type"] = project_type_tuple
    
    if portfolio_category_tuple:
        where_clauses.append("pro.custom_portfolio_category IN %(portfolio_category)s")
        params["portfolio_category"] = portfolio_category_tuple
    
    if txt:
        where_clauses.append("pro.name LIKE %(txt)s")
        params["txt"] = f"%{txt}%"

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
        ORDER BY pp.parent
    """

    try:
        results = frappe.db.sql(query, params, as_dict=True)
    except Exception as e:
        frappe.log_error(f"Error in get_projects_by_partner: {str(e)}", "Project Filter Error")
        return []

    return [{"value": row.project, "description": row.project} for row in results]

@frappe.whitelist()
def get_partner_list():
    # تجاوز الصلاحيات لكن نقيد النتائج فقط بالـ Partners و CEO
    return frappe.get_all(
        "Employee",
        filters={"designation": ["in", ["Partner", "CEO"]]},
        fields=["name", "employee_name"],
        ignore_permissions=True
    )
