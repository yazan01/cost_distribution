import frappe
from collections import defaultdict

def execute(filters=None):
    filters = filters or {}
    project = filters.get("project")

    raw_data = []

    if project:
        conditions = f"AND p.project = '{project}'"
        raw_data = frappe.db.sql(f"""
            SELECT  
                cd.posting_date,
                e.employee,
                e.employee_name,
                e.`level`,
                p.project,
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

    # تجميع النتائج حسب project/employee/level/ctc
    grouped = defaultdict(lambda: {
        "project": "",
        "employee": "",
        "employee_name": "",
        "level": "",
        "ctc": 0.0,
        "months": []
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
        {"label": "Months", "fieldname": "months", "fieldtype": "Data", "width": 250}
    ]

    return columns, final_data
