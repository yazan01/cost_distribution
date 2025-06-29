import frappe

def execute(filters=None):
    project = filters.get("project")
    

    conditions = "1=1"
    if project:
        conditions += f" AND project = '{project}'"
  

    data = frappe.db.sql(f"""
        SELECT 
            `year`, project, parent, ctc
        FROM 
            `tabLevel Rate`
        WHERE 
            {conditions}
        ORDER BY 
            `year` , parent 
    """, as_dict=True)

    # If no pricing sheet Project is null
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
        {"label": "Project", "fieldname": "project", "fieldtype": "Link", "option": "Project", "width": 180},
        {"label": "Level", "fieldname": "level", "fieldtype": "Data", "width": 180},
        {"label": "CTC", "fieldname": "ctc", "fieldtype": "Float", "width": 180},
    ]

    return columns, data
