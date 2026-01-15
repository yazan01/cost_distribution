from collections import OrderedDict
import frappe
from frappe import _, _dict

def execute(filters):
    columns = [
        {"label": "Period", "fieldname": "period", "fieldtype": "Data", "width": 120},
        {"label": "CTC Cost", "fieldname": "total_ctc", "fieldtype": "Float", "width": 200},
        {"label": "Actual Cost", "fieldname": "total_actual", "fieldtype": "Float", "width": 200},
        {"label": "Revenue", "fieldname": "total_revenue", "fieldtype": "Float", "width": 200},
        {"label": "Profit AND Loss on CTC Cost", "fieldname": "profit_loss_ctc", "fieldtype": "Float", "width": 240},
        {"label": "Profit AND Loss on Actual Cost", "fieldname": "profit_loss_actual", "fieldtype": "Float", "width": 240},
    ]

    data = get_project_data(filters)
    return columns, data

def get_project_data(filters):
    project_filter = filters.get("project")
    partner_filter = filters.get("partner")
    project_type_filter = filters.get("project_type")
    portfolio_category_filter = filters.get("portfolio_category")
    view_filter = filters.get("view")
    aggregated_filter = filters.get("aggregated")
    persentage = filters.get("persentage")
    
    # Convert project_filter list to tuple for SQL IN clause; if None or empty, use empty tuple
    if project_filter:
        if isinstance(project_filter, list):
            project_filter_tuple = tuple(project_filter)
        else:
            project_filter_tuple = (project_filter,)
    else:
        project_filter_tuple = ()

    # Handle multi-select project_type_filter
    if project_type_filter:
        if isinstance(project_type_filter, str):
            project_type_list = [pt.strip() for pt in project_type_filter.split(',') if pt.strip()]
        elif isinstance(project_type_filter, list):
            project_type_list = project_type_filter
        else:
            project_type_list = [project_type_filter]
        project_type_tuple = tuple(project_type_list) if project_type_list else ()
    else:
        project_type_tuple = ()

    # Handle multi-select portfolio_category_filter
    if portfolio_category_filter:
        if isinstance(portfolio_category_filter, str):
            portfolio_category_list = [pc.strip() for pc in portfolio_category_filter.split(',') if pc.strip()]
        elif isinstance(portfolio_category_filter, list):
            portfolio_category_list = portfolio_category_filter
        else:
            portfolio_category_list = [portfolio_category_filter]
        portfolio_category_tuple = tuple(portfolio_category_list) if portfolio_category_list else ()
    else:
        portfolio_category_tuple = ()

    # Build where clauses dynamically
    where_clauses = ["pp.partner = %(partner_filter)s"]

    if project_filter_tuple:
        where_clauses.append("pp.parent IN %(project_filter)s")
    if project_type_tuple:
        where_clauses.append("pro.project_type IN %(project_type_filter)s")
    if portfolio_category_tuple:
        where_clauses.append("pro.custom_portfolio_category IN %(portfolio_category_filter)s")

    where_sql = " AND ".join(where_clauses)

    query = f"""
        SELECT 
            pp.parent AS project_id,
            pp.percentage AS percentage
        FROM 
            `tabPartners Percentage` AS pp 
        JOIN 
            `tabProject` AS pro ON pro.name = pp.parent 
        WHERE 
            {where_sql}
    """

    params = {
        "partner_filter": partner_filter,
        "project_filter": project_filter_tuple,
        "project_type_filter": project_type_tuple,
        "portfolio_category_filter": portfolio_category_tuple
    }

    all_projects = frappe.db.sql(query, params, as_dict=True)

    if persentage:
        project_percentages = {p["project_id"]: float(p["percentage"] or 0) / 100 for p in all_projects}
    else:
        project_percentages = {p["project_id"]: float(100) / 100 for p in all_projects}
    
    # project_percentages = {p["project_id"]: float(p["percentage"] or 0) / 100 for p in all_projects}
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

    financial_data = frappe.db.sql("""
        SELECT 
            gl.project AS project_id,
            CONCAT(LPAD(MONTH(gl.posting_date), 2, '0'), '-', YEAR(gl.posting_date)) AS month_year,
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
            AND gl.docstatus = 1 AND gl.is_cancelled = 0 AND gl.remarks NOT REGEXP "CAPITALIZATION"
        GROUP BY gl.project, YEAR(gl.posting_date), MONTH(gl.posting_date)
        ORDER BY gl.project, YEAR(gl.posting_date), MONTH(gl.posting_date)
    """, {"project_ids": project_ids, 'partner_filter': partner_filter, 'act': '5%', 'rev': '4%'}, as_dict=True)

    ctc_data = frappe.db.sql("""
        SELECT 
            S.project AS project_id,
            CONCAT(LPAD(MONTH(D.posting_date), 2, '0'), '-', YEAR(D.posting_date)) AS month_year,
            ROUND(SUM(S.total_cost_of_project), 2) AS ctc_cost
        FROM `tabProject Summary CTC` S
        JOIN `tabCTC Distribution` D ON S.parent = D.name
        WHERE 
            S.project IN %(project_ids)s 
        GROUP BY S.project, YEAR(D.posting_date), MONTH(D.posting_date)
        ORDER BY S.project, YEAR(D.posting_date), MONTH(D.posting_date)
    """, {"project_ids": project_ids}, as_dict=True)

    indirect_costs = []
    if projects_list_notexp:
        indirect_costs = frappe.db.sql("""
            SELECT 
                gl.project AS project_id,
                CONCAT(LPAD(MONTH(gl.posting_date), 2, '0'), '-', YEAR(gl.posting_date)) AS month_year,
                SUM((gl.debit - gl.credit) * afc.currency) AS indirect_cost
            FROM `tabAccounts For CTC` AS afc
            JOIN `tabGL Entry` AS gl ON afc.account = gl.account 
            WHERE 
                gl.project IN %(project_ids)s 
                AND afc.type = 'Indirect' 
                AND gl.docstatus = 1 
                AND gl.is_cancelled = 0 
                AND gl.account LIKE %(acc)s
                AND gl.remarks NOT REGEXP "Cost Distribution POP" AND gl.remarks NOT REGEXP "CAPITALIZATION"
            GROUP BY gl.project, YEAR(gl.posting_date), MONTH(gl.posting_date)
            ORDER BY gl.project, YEAR(gl.posting_date), MONTH(gl.posting_date)
        """, {"project_ids": projects_list_notexp, 'acc': '5%'}, as_dict=True)

    indirect_costs_exp = []
    if projects_list_exp:
        indirect_costs_exp = frappe.db.sql("""
            SELECT 
                gl.project AS project_id,
                CONCAT(LPAD(MONTH(gl.posting_date), 2, '0'), '-', YEAR(gl.posting_date)) AS month_year,
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
            GROUP BY gl.project, YEAR(gl.posting_date), MONTH(gl.posting_date)
            ORDER BY gl.project, YEAR(gl.posting_date), MONTH(gl.posting_date)
        """, {"project_ids": projects_list_exp, 'acc': '5%'}, as_dict=True)

    # تجميع كل المفاتيح لتوحيد العرض
    all_keys = set()
    for d in financial_data:
        all_keys.add((d["project_id"], d["month_year"]))
    for d in ctc_data:
        all_keys.add((d["project_id"], d["month_year"]))
    for d in indirect_costs:
        all_keys.add((d["project_id"], d["month_year"]))
    for d in indirect_costs_exp:  
        all_keys.add((d["project_id"], d["month_year"]))

    financial_lookup = {(d["project_id"], d["month_year"]): d for d in financial_data}
    ctc_lookup = {(d["project_id"], d["month_year"]): d["ctc_cost"] for d in ctc_data}
    indirect_lookup = {(d["project_id"], d["month_year"]): d["indirect_cost"] for d in indirect_costs}
    indirect_lookup_exp = {(d["project_id"], d["month_year"]): d["indirect_cost"] for d in indirect_costs_exp}
    
    result = OrderedDict()

    for key in sorted(all_keys):
        project_id, month_year = key
        percentage = project_percentages.get(project_id, 0)

        financial_entry = financial_lookup.get(key, {})
        ctc_cost = ctc_lookup.get(key, 0.0)
        indirect_cost = indirect_lookup.get(key, 0.0)

        indirect_costs_exp_val = indirect_lookup_exp.get(key, 0.0)
        
        total_ctc = ctc_cost + indirect_cost + indirect_costs_exp_val

        actual_cost = financial_entry.get("actual_cost", 0.0)
        revenue = financial_entry.get("revenue", 0.0)

        total_ctc *= percentage
        actual_cost *= percentage
        revenue *= percentage

        result[key] = {
            "period": month_year,
            "total_ctc": round(total_ctc, 2),
            "total_actual": round(actual_cost, 2),
            "total_revenue": round(revenue, 2),
            "profit_loss_ctc": round(revenue - total_ctc, 2),
            "profit_loss_actual": round(revenue - actual_cost, 2),
        }

    aggregated_result = OrderedDict()

    for (project_id, month_year), values in result.items():
        period_key = month_year.split("-")[1] if view_filter == "Year" else month_year

        if period_key not in aggregated_result:
            aggregated_result[period_key] = {
                "period": period_key,
                "total_ctc": 0.0,
                "total_actual": 0.0,
                "total_revenue": 0.0,
                "profit_loss_ctc": 0.0,
                "profit_loss_actual": 0.0,
            }

        aggregated_result[period_key]["total_ctc"] += values["total_ctc"]
        aggregated_result[period_key]["total_actual"] += values["total_actual"]
        aggregated_result[period_key]["total_revenue"] += values["total_revenue"]
        aggregated_result[period_key]["profit_loss_ctc"] += values["profit_loss_ctc"]
        aggregated_result[period_key]["profit_loss_actual"] += values["profit_loss_actual"]

    for item in aggregated_result.values():
        for key in ["total_ctc", "total_actual", "total_revenue", "profit_loss_ctc", "profit_loss_actual"]:
            item[key] = round(item[key], 2)

    # ترتيب حسب الفترة
    sorted_data = sorted(
        aggregated_result.values(),
        key=lambda x: (
            int(x["period"]) if view_filter == "Year"
            else (int(x["period"].split("-")[1]), int(x["period"].split("-")[0]))
        )
    )

    if aggregated_filter:
        cumulative_ctc = 0.0
        cumulative_actual = 0.0
        cumulative_revenue = 0.0
        cumulative_profit_ctc = 0.0
        cumulative_profit_actual = 0.0

        for item in sorted_data:
            cumulative_ctc += item["total_ctc"]
            cumulative_actual += item["total_actual"]
            cumulative_revenue += item["total_revenue"]
            cumulative_profit_ctc += item["profit_loss_ctc"]
            cumulative_profit_actual += item["profit_loss_actual"]

            item["total_ctc"] = round(cumulative_ctc, 2)
            item["total_actual"] = round(cumulative_actual, 2)
            item["total_revenue"] = round(cumulative_revenue, 2)
            item["profit_loss_ctc"] = round(cumulative_profit_ctc, 2)
            item["profit_loss_actual"] = round(cumulative_profit_actual, 2)

    return sorted_data


@frappe.whitelist()
def get_projects_by_partner(partner, txt="", project_type=None, portfolio_category=None):
    # Handle multi-select project_type
    project_type_tuple = ()
    if project_type:
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
        if isinstance(portfolio_category, str):
            portfolio_category_list = [pc.strip() for pc in portfolio_category.split(',') if pc.strip()]
        elif isinstance(portfolio_category, list):
            portfolio_category_list = portfolio_category
        else:
            portfolio_category_list = [portfolio_category]
        if portfolio_category_list:
            portfolio_category_tuple = tuple(portfolio_category_list)

    # نبني شروط WHERE ديناميكيًا
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
    """

    results = frappe.db.sql(query, params, as_dict=True)

    # إرجاع القائمة بصيغة MultiSelectList
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
