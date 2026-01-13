from collections import OrderedDict
import frappe
from frappe import _, _dict
from datetime import datetime

def execute(filters):
    from_date = filters.get("from_date")
    to_date = filters.get("to_date")
    show_ctc = filters.get("show_ctc")
    
    if not from_date or not to_date:
        frappe.throw(_("Please select the start and end dates"))
    
    # توليد الأعمدة الديناميكية بناءً على التواريخ
    columns = get_dynamic_columns(from_date, to_date, show_ctc)
    
    # جلب البيانات
    data = get_project_data(filters)
    
    return columns, data

def get_dynamic_columns(from_date, to_date, show_ctc):
    """توليد الأعمدة بناءً على السنوات المختارة"""
    
    from_year = datetime.strptime(str(from_date), "%Y-%m-%d").year
    to_year = datetime.strptime(str(to_date), "%Y-%m-%d").year
    
    # الأعمدة الأساسية (ثابتة)
    columns = [
        {"label": "Project ID", "fieldname": "project_id", "fieldtype": "Link", "options": "Project", "width": 120},
        {"label": "Project Name A", "fieldname": "project_name_a", "fieldtype": "Data", "width": 250},
        {"label": "Project Name E", "fieldname": "project_name_e", "fieldtype": "Data", "width": 250},
        {"label": "Project Type", "fieldname": "project_type", "fieldtype": "Data", "width": 150},
        {"label": "Project Status", "fieldname": "project_status", "fieldtype": "Data", "width": 150},
        {"label": "Client", "fieldname": "client", "fieldtype": "Data", "width": 250},
        {"label": "Project Manager", "fieldname": "project_manager", "fieldtype": "Link", "options": "Employee", "width": 180},
        {"label": "Project Manager Name", "fieldname": "project_manager_name", "fieldtype": "Data", "width": 200},
    ]
    
    # إضافة أعمدة CTC لكل سنة
    if show_ctc:
        for year in range(from_year, to_year + 1):
            columns.append({
                "label": f"Year {year} CTC Cost",
                "fieldname": f"ctc_{year}",
                "fieldtype": "Float",
                "width": 150
            })
        
        # عمود المجموع للـ CTC
        columns.append({
            "label": "Total CTC Cost",
            "fieldname": "total_ctc",
            "fieldtype": "Float",
            "width": 150
        })
    
    # إضافة أعمدة Actual لكل سنة
    for year in range(from_year, to_year + 1):
        columns.append({
            "label": f"Year {year} Actual Cost",
            "fieldname": f"actual_{year}",
            "fieldtype": "Float",
            "width": 150
        })
    
    # عمود المجموع للـ Actual
    columns.append({
        "label": "Total Actual Cost",
        "fieldname": "total_actual",
        "fieldtype": "Float",
        "width": 150
    })
    
    # إضافة أعمدة Revenue لكل سنة
    for year in range(from_year, to_year + 1):
        columns.append({
            "label": f"Year {year} Revenue",
            "fieldname": f"revenue_{year}",
            "fieldtype": "Float",
            "width": 150
        })
    
    # عمود المجموع للـ Revenue
    columns.append({
        "label": "Total Revenue",
        "fieldname": "total_revenue",
        "fieldtype": "Float",
        "width": 150
    })

    
    if show_ctc:
        columns.append({"label": "Profit AND Loss on CTC Cost", "fieldname": "profit_loss_ctc", "fieldtype": "Float", "width": 200},)
        
    # أعمدة الربح والخسارة
    columns.extend([        
        {"label": "Profit AND Loss on Actual Cost", "fieldname": "profit_loss_actual", "fieldtype": "Float", "width": 200},
    ])
    
    return columns

def get_project_data(filters):
    project_filter = filters.get("project")
    partner_filter = filters.get("partner")
    project_type_filter = filters.get("project_type")
    project_status = filters.get("status")
    customer = filters.get("customer")
    from_date = filters.get("from_date")
    to_date = filters.get("to_date")
    
    from_year = datetime.strptime(str(from_date), "%Y-%m-%d").year
    to_year = datetime.strptime(str(to_date), "%Y-%m-%d").year
    years_list = list(range(from_year, to_year + 1))
    
    # جلب المشاريع
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


    #update
    projects_exp = frappe.db.sql("SELECT name FROM `tabProject Accounts For CTC`", as_list=True)
    projects_list_exp_1 = [project[0] for project in projects_exp]

    projects_list_notexp = list(
        set(project_ids) - set(projects_list_exp_1)
    )
    projects_list_exp = list(
        set(projects_list_exp_1) & set(project_ids)
    )

    
    # جلب البيانات المالية
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
            AND gl.posting_date BETWEEN %(from_date)s AND %(to_date)s
            AND YEAR(gl.posting_date) IN %(years_list)s
            AND gl.docstatus = 1 AND gl.is_cancelled = 0 AND gl.remarks NOT REGEXP "CAPITALIZATION"
        GROUP BY gl.project, YEAR(gl.posting_date)
    """, {
        "project_ids": project_ids, 
        'act': '5%', 
        'rev': '4%',
        'from_date': from_date,
        'to_date': to_date,
        'years_list': years_list
    }, as_dict=True)
    
    # جلب بيانات CTC
    ctc_data = frappe.db.sql("""
        SELECT 
            S.project AS project_id,
            YEAR(D.posting_date) AS year,
            ROUND(SUM(S.total_cost_of_project), 2) AS ctc_cost
        FROM `tabProject Summary CTC` S
        JOIN `tabCTC Distribution` D ON S.parent = D.name
        WHERE 
            S.project IN %(project_ids)s 
            AND D.posting_date BETWEEN %(from_date)s AND %(to_date)s
            AND YEAR(D.posting_date) IN %(years_list)s
        GROUP BY S.project, YEAR(D.posting_date)
    """, {
        "project_ids": project_ids,
        'from_date': from_date,
        'to_date': to_date,
        'years_list': years_list
    }, as_dict=True)
    
    # جلب التكاليف غير المباشرة
    indirect_costs = []
    if projects_list_notexp:
        indirect_costs = frappe.db.sql("""
            SELECT 
                gl.project AS project_id,
                YEAR(gl.posting_date) AS year,
                SUM((gl.debit - gl.credit) * afc.currency) AS indirect_cost
            FROM `tabAccounts For CTC` AS afc
            JOIN `tabGL Entry` AS gl ON afc.account = gl.account 
            WHERE 
                gl.project IN %(project_ids)s 
                AND gl.posting_date BETWEEN %(from_date)s AND %(to_date)s
                AND YEAR(gl.posting_date) IN %(years_list)s
                AND afc.type = 'Indirect' 
                AND gl.docstatus = 1 
                AND gl.is_cancelled = 0 
                AND gl.account LIKE %(acc)s
                AND gl.remarks NOT REGEXP "Cost Distribution POP" AND gl.remarks NOT REGEXP "CAPITALIZATION"
            GROUP BY gl.project, YEAR(gl.posting_date)
        """, {
            "project_ids": projects_list_notexp, 
            'acc': '5%',
            'from_date': from_date,
            'to_date': to_date,
            'years_list': years_list
        }, as_dict=True)


    indirect_costs_exp = []
    if projects_list_exp:
        indirect_costs_exp = frappe.db.sql("""
            SELECT 
                gl.project AS project_id,
                YEAR(gl.posting_date) AS year,
                SUM((gl.debit - gl.credit) * afc.currency) AS indirect_cost
            FROM `tabAccount VS Year CTC` AS avyc
            JOIN `tabAccounts For CTC` AS afc ON avyc.account_for_ctc = afc.account
            JOIN `tabGL Entry` AS gl ON gl.account = afc.account 
            WHERE 
                gl.project IN %(project_ids)s 
                AND avyc.parent = gl.project
                AND gl.posting_date BETWEEN %(from_date)s AND %(to_date)s
                AND YEAR(gl.posting_date) IN %(years_list)s
                AND YEAR(gl.posting_date) = avyc.year
                AND afc.type = 'Indirect' 
                AND gl.docstatus = 1 
                AND gl.is_cancelled = 0 
                AND gl.account LIKE %(acc)s
                AND gl.remarks NOT REGEXP "Cost Distribution POP" AND gl.remarks NOT REGEXP "CAPITALIZATION"
            GROUP BY gl.project, YEAR(gl.posting_date)
        """, {
            "project_ids": projects_list_exp, 
            'acc': '5%',
            'from_date': from_date,
            'to_date': to_date,
            'years_list': years_list
        }, as_dict=True)


    # تحويل البيانات إلى قواميس للوصول السريع
    financial_dict = {(f["project_id"], f["year"]): f for f in financial_data}
    ctc_dict = {(c["project_id"], c["year"]): c["ctc_cost"] for c in ctc_data}
    indirect_cost_dict = {(t["project_id"], t["year"]): t["indirect_cost"] for t in indirect_costs}
    indirect_cost_dict_exp = {(t["project_id"], t["year"]): t["indirect_cost"] for t in indirect_costs_exp}

    data = []
    for project in projects:
        project_id = project["project_id"]
        
        # بناء الصف بشكل ديناميكي
        row = {**project}
        
        # متغيرات المجاميع
        total_ctc = 0
        total_actual = 0
        total_revenue = 0
        
        # إضافة البيانات لكل سنة
        for year in years_list:
            # CTC
            ctc_value = ctc_dict.get((project_id, year), 0) + indirect_cost_dict.get((project_id, year), 0) + indirect_cost_dict_exp.get((project_id, year), 0)
            row[f"ctc_{year}"] = ctc_value
            total_ctc += ctc_value
            
            # Actual Cost
            actual_value = financial_dict.get((project_id, year), {}).get("actual_cost", 0)
            row[f"actual_{year}"] = actual_value
            total_actual += actual_value
            
            # Revenue
            revenue_value = financial_dict.get((project_id, year), {}).get("revenue", 0)
            row[f"revenue_{year}"] = revenue_value
            total_revenue += revenue_value
        
        # إضافة المجاميع
        row["total_ctc"] = total_ctc
        row["total_actual"] = total_actual
        row["total_revenue"] = total_revenue
        row["profit_loss_ctc"] = total_revenue - total_ctc
        row["profit_loss_actual"] = total_revenue - total_actual
        
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
