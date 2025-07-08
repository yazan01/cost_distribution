import frappe
from collections import defaultdict

def execute(filters=None):
    filters = filters or {}
    project = filters.get("project")

    raw_data = []
    raw_data_2 = []

    if project:
        conditions = f"AND p.project = '{project}'"
        raw_data = frappe.db.sql(f"""
            SELECT  
                cd.posting_date,
                e.employee,
                e.employee_name,
                e.`level`,
                p.project,
                p.total_cost_of_project AS total,
                COALESCE(lr_match.ctc, lr_null.ctc) AS ctc
            FROM 
                `tabCTC Distribution` AS cd
            LEFT JOIN 
                `tabEmployee Cost Table CTC` AS e
            ON 
                cd.name = e.parent
            LEFT JOIN 
                `tabProject Summary CTC` AS p
            ON 
                cd.name = p.parent
                AND e.employee = p.employee
            LEFT JOIN 
                `tabLevel Rate` AS lr_match
            ON 
                e.`level` = lr_match.parent
                AND YEAR(cd.posting_date) = lr_match.`year`
                AND lr_match.project = p.project
            LEFT JOIN 
                `tabLevel Rate` AS lr_null
            ON 
                e.`level` = lr_null.parent
                AND YEAR(cd.posting_date) = lr_null.`year`
                AND lr_null.project IS NULL
            WHERE 
                cd.docstatus = 1
                AND e.employment_type = "Permanent"
                {conditions}
        """, as_dict=True)

         raw_data_2 = frappe.db.sql(f"""
            SELECT  
                cd.posting_date,
                e.employee,
                e.employee_name,
                COALESCE(e.`level`, 'null') AS level,
                p.project,
                p.total_cost_of_project AS total,
                0 AS ctc
            FROM 
                `tabCTC Distribution` AS cd
            LEFT JOIN 
                `tabEmployee Cost Table CTC` AS e
            ON 
                cd.name = e.parent
            LEFT JOIN 
                `tabProject Summary CTC` AS p
            ON 
                cd.name = p.parent
                AND e.employee = p.employee
            WHERE 
                cd.docstatus = 1
                AND e.employment_type = "Subcontract"
                {conditions}
        """, as_dict=True)

    # تجميع النتائج حسب project/employee/level/ctc
    grouped = defaultdict(lambda: {
        "project": "",
        "employee": "",
        "employee_name": "",
        "level": "",
        "ctc": 0.0,
        "months": [],
        "total_actual_ctc": 0.0
    })

    for row in raw_data:
        key = (row.project, row.employee, row.level, row.ctc)
        group = grouped[key]

        group["project"] = row.project
        group["employee"] = row.employee
        group["employee_name"] = row.employee_name
        group["level"] = row.level
        group["ctc"] = row.ctc
        group["months"].append(row.posting_date.strftime("%Y-%m"))  # جمع التاريخ بالشهر فقط
        group["total_actual_ctc"] = group["total_actual_ctc"] + row.total

    for row in raw_data_2:
        key = (row.project, row.employee, row.level, row.ctc)
        group = grouped[key]

        group["project"] = row.project
        group["employee"] = row.employee
        group["employee_name"] = row.employee_name
        group["level"] = row.level
        group["ctc"] = row.ctc
        group["months"].append(row.posting_date.strftime("%Y-%m"))  # جمع التاريخ بالشهر فقط
        group["total_actual_ctc"] = group["total_actual_ctc"] + row.total

    # تحويل dict إلى list مع months مفصولة بفواصل
    final_data = []
    for entry in grouped.values():
        entry["months"] = ", ".join(sorted(set(entry["months"])))
        final_data.append(entry)

    columns = [
        {"label": "Project", "fieldname": "project", "fieldtype": "Link", "options": "Project", "width": 180},
        {"label": "Employee", "fieldname": "employee", "fieldtype": "Data", "width": 180},
        {"label": "Employee Name", "fieldname": "employee_name", "fieldtype": "Data", "width": 250},
        {"label": "Level", "fieldname": "level", "fieldtype": "Data", "width": 180},
        {"label": "CTC", "fieldname": "ctc", "fieldtype": "Float", "width": 180},
        {"label": "Months", "fieldname": "months", "fieldtype": "Data", "width": 250},
        {"label": "Total Actual CTC", "fieldname": "total_actual_ctc", "fieldtype": "Float", "width": 180}
    ]

    return columns, final_data
