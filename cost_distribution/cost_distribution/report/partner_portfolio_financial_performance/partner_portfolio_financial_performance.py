from collections import OrderedDict
from datetime import datetime
from dateutil.relativedelta import relativedelta
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
    view_filter = filters.get("view") or "Month"

    all_projects = frappe.db.sql("""
        SELECT 
            pp.parent AS project_id,
            pp.percentage AS percentage
        FROM 
            `tabPartners Percentage` AS pp 
        JOIN 
            `tabProject` AS pro ON pro.name = pp.parent 
        WHERE 
            pp.partner = %(partner_filter)s
            AND (%(project_type_filter)s IS NULL OR pro.project_type = %(project_type_filter)s)
            AND (%(portfolio_category_filter)s IS NULL OR pro.custom_portfolio_category = %(portfolio_category_filter)s)
    """, {
        "partner_filter": partner_filter,
        "project_type_filter": project_type_filter,
        "portfolio_category_filter": portfolio_category_filter
    }, as_dict=True)

    if project_filter:
        all_projects = [p for p in all_projects if p["project_id"] == project_filter]

    project_percentages = {p["project_id"]: float(p["percentage"] or 0) / 100 for p in all_projects}
    project_ids = list(project_percentages.keys())

    if not project_ids:
        return []

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
            AND gl.docstatus = 1 AND gl.is_cancelled = 0 
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
        GROUP BY S.project, YEAR(D.posting_date) , MONTH(D.posting_date)
        ORDER BY S.project, YEAR(D.posting_date) , MONTH(D.posting_date)
    """, {"project_ids": project_ids}, as_dict=True)

    indirect_costs = frappe.db.sql("""
        SELECT 
            gl.project AS project_id,
            CONCAT(LPAD(MONTH(gl.posting_date), 2, '0'), '-', YEAR(gl.posting_date)) AS month_year,
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
            AND gl.remarks NOT REGEXP "Cost Distribution"
        GROUP BY gl.project, YEAR(gl.posting_date), MONTH(gl.posting_date)
        ORDER BY gl.project, YEAR(gl.posting_date), MONTH(gl.posting_date)
    """, {"project_ids": project_ids, 'acc': '5%'}, as_dict=True)

    def parse_month_year(s):
        return datetime.strptime(s, "%m-%Y")

    # === استخراج كل التواريخ لتحديد الفترة الزمنية ===
    all_dates = set()
    for d in financial_data + ctc_data + indirect_costs:
        if "month_year" in d:
            all_dates.add(d["month_year"])

    if not all_dates:
        return []

    min_date = min(parse_month_year(d) for d in all_dates)
    max_date = max(parse_month_year(d) for d in all_dates)

    all_periods = []
    current = min_date
    while current <= max_date:
        if view_filter == "Year":
            period_label = current.strftime("%Y")
        else:
            period_label = current.strftime("%m-%Y")
        all_periods.append(period_label)
        current += relativedelta(months=1)

    data_map = {}

    for entry in financial_data:
        period = entry["month_year"]
        if view_filter == "Year":
            period = period.split("-")[1]
        key = (entry["project_id"], period)
        data_map.setdefault(key, {"actual": 0.0, "revenue": 0.0})
        data_map[key]["actual"] += entry["actual_cost"] * project_percentages.get(entry["project_id"], 0)
        data_map[key]["revenue"] += entry["revenue"] * project_percentages.get(entry["project_id"], 0)

    for entry in ctc_data:
        period = entry["month_year"]
        if view_filter == "Year":
            period = period.split("-")[1]
        key = (entry["project_id"], period)
        data_map.setdefault(key, {})
        data_map[key]["ctc"] = entry["ctc_cost"] * project_percentages.get(entry["project_id"], 0)

    for entry in indirect_costs:
        period = entry["month_year"]
        if view_filter == "Year":
            period = period.split("-")[1]
        key = (entry["project_id"], period)
        data_map.setdefault(key, {})
        if "ctc" not in data_map[key]:
            data_map[key]["ctc"] = 0.0
        data_map[key]["ctc"] += entry["indirect_cost"] * project_percentages.get(entry["project_id"], 0)

    aggregated = OrderedDict()
    for (proj_id, period), values in data_map.items():
        if period not in aggregated:
            aggregated[period] = {
                "period": period,
                "total_ctc": 0.0,
                "total_actual": 0.0,
                "total_revenue": 0.0,
                "profit_loss_ctc": 0.0,
                "profit_loss_actual": 0.0,
            }
        aggregated[period]["total_ctc"] += values.get("ctc", 0.0)
        aggregated[period]["total_actual"] += values.get("actual", 0.0)
        aggregated[period]["total_revenue"] += values.get("revenue", 0.0)

    for row in aggregated.values():
        row["profit_loss_ctc"] = round(row["total_revenue"] - row["total_ctc"], 2)
        row["profit_loss_actual"] = round(row["total_revenue"] - row["total_actual"], 2)
        row["total_ctc"] = round(row["total_ctc"], 2)
        row["total_actual"] = round(row["total_actual"], 2)
        row["total_revenue"] = round(row["total_revenue"], 2)

    return sorted(
        aggregated.values(),
        key=lambda x: parse_month_year("01-" + x["period"]) if view_filter == "Year" else parse_month_year(x["period"])
    )
