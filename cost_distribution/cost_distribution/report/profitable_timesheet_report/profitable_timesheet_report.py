import frappe

def execute(filters=None):
    from_date = filters.get("from_date")
    to_date = filters.get("to_date")
    employee = filters.get("employee")

    conditions = "1=1"
    if from_date and to_date:
        conditions += f" AND t.time_date BETWEEN '{from_date}' AND '{to_date}'"
    if employee:
        conditions += f" AND ts.employee = '{employee}'"

    # Exclude rows with NULL allocation type
    conditions += " AND p.custom_allocation_type IS NOT NULL"

    data = frappe.db.sql("""
        SELECT 
            ts.employee,
            e.employee_name,
            SUM(t.hours) AS total_hours,
            SUM(CASE WHEN p.custom_allocation_type = 'Billable' THEN t.hours ELSE 0 END) AS billable_hours,
            SUM(CASE WHEN p.custom_allocation_type = 'Partially Billable' 
                     THEN (t.hours * IFNULL(p.custom_allocation_percent, 0) / 100) ELSE 0 END) AS partial_billable_hours
        FROM `tabTimesheet Detail` t
        JOIN `tabTimesheet` ts ON t.parent = ts.name
        LEFT JOIN `tabProject` p ON t.project = p.name
        LEFT JOIN `tabEmployee` e ON ts.employee = e.name
        WHERE {conditions}
        AND e.gender = 'Female'
        GROUP BY ts.employee, e.employee_name
    """.format(conditions=conditions), as_dict=True)

    for row in data:
        total = row.total_hours or 0
        total_profitable = (row.billable_hours or 0) + (row.partial_billable_hours or 0)
        row.total_profitable_hours = total_profitable
        row.profitable_ratio = round((total_profitable / total) * 100, 2) if total else 0

    columns = [
        {"label": "Employee", "fieldname": "employee", "fieldtype": "Link", "options": "Employee", "width": 150},
        {"label": "Employee Name", "fieldname": "employee_name", "fieldtype": "Data", "width": 180},
        {"label": "Total Hours", "fieldname": "total_hours", "fieldtype": "Float", "width": 120},
        {"label": "Profitable Hours", "fieldname": "total_profitable_hours", "fieldtype": "Float", "width": 140},
        {"label": "Profitability %", "fieldname": "profitable_ratio", "fieldtype": "Percent", "width": 140},
    ]

    return columns, data
