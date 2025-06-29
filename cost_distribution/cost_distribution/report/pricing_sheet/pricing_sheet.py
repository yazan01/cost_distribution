import frappe

def execute(filters=None):
    filters = filters or {}
    project = filters.get("project")

    raw_data = []

    if project:
        conditions = f"project = '{project}'"
        raw_data = frappe.db.sql(f"""
            SELECT 
                `year`, project, parent, ctc
            FROM 
                `tabLevel Rate`
            WHERE 
                {conditions}
            ORDER BY 
                `year`, parent
        """, as_dict=True)

    # إذا لم يتم تمرير project أو النتيجة فارغة، نحاول الحصول على النتائج where project is null
    if not raw_data:
        raw_data = frappe.db.sql("""
            SELECT 
                `year`, project, parent, ctc
            FROM 
                `tabLevel Rate`
            WHERE 
                project IS NULL
            ORDER BY 
                `year`, parent
        """, as_dict=True)

    # تجهيز البيانات
    data = []
    for row in raw_data:
        data.append({
            "year": row.year,
            "project": row.project,
            "level": row.parent,
            "ctc": row.ctc
        })

    columns = [
        {"label": "Year", "fieldname": "year", "fieldtype": "Data", "width": 180},
        {"label": "Project", "fieldname": "project", "fieldtype": "Link", "options": "Project", "width": 180},
        {"label": "Level", "fieldname": "level", "fieldtype": "Data", "width": 180},
        {"label": "CTC", "fieldname": "ctc", "fieldtype": "Float", "width": 180},
    ]

    return columns, data
