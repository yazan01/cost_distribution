import frappe

def execute(filters=None):
    from_date = filters.get("from_date")
    to_date = filters.get("to_date")
    employee = filters.get("employee")
    unit = filters.get("unit")
    employee_status = filters.get("employee_status")
    portfolio_type = filters.get("portfolio_type")
    level = filters.get("level")
    employment_type = filters.get("employment_type")

    conditions = "1=1"
    if from_date and to_date:
        conditions += f" AND ts.start_date BETWEEN '{from_date}' AND '{to_date}'"
    if employee:
        conditions += f" AND ts.employee = '{employee}'"
    if unit:
        conditions += f" AND e.custom_supporting_services__consultant = '{unit}'"
    if employee_status:
        conditions += f" AND e.status = '{employee_status}'"
    
    # Handle multi-select portfolio_type filter
    # Convert portfolio_types list to tuple for SQL IN clause; if None or empty, use empty tuple
    if portfolio_type:
        if isinstance(portfolio_type, str):
            # Convert comma-separated string to list
            portfolio_types = tuple(pt.strip() for pt in portfolio_type.split(',') if pt.strip())
        elif isinstance(portfolio_type, (list, tuple)):
            portfolio_types = tuple(portfolio_type)
        else:
            portfolio_types = (portfolio_type,)
        
        if portfolio_types:
            # Use parameterized query with tuple for SQL IN clause
            placeholders = ', '.join(['%s'] * len(portfolio_types))
            conditions += f" AND p.custom_portfolio_category IN ({placeholders})"
    else:
        portfolio_types = ()
    
    if level:
        conditions += f" AND d.custom_level = '{level}'"
    if employment_type:
        conditions += f" AND e.employment_type = '{employment_type}'"

    # Exclude rows with NULL allocation type
    conditions += " AND p.custom_allocation_type IS NOT NULL"

    # Prepare query parameters
    query_params = []
    
    # Build the query with portfolio_types if provided
    if portfolio_type and portfolio_types:
        query_params.extend(portfolio_types)

    data = frappe.db.sql(f"""
        SELECT 
            ts.employee,
            e.employee_name,
            e.employment_type,
            SUM(CASE WHEN p.custom_allocation_type != 'NA' THEN t.hours ELSE 0 END) AS total_hours,
            SUM(CASE WHEN p.custom_allocation_type = 'Billable' THEN t.hours ELSE 0 END) AS billable_hours,
            SUM(CASE WHEN p.custom_allocation_type = 'Partially Billable' 
                     THEN (t.hours * IFNULL(p.custom_allocation_percent, 0) / 100) ELSE 0 END) AS partial_billable_hours,
            SUM(CASE WHEN p.custom_allocation_type = 'NA' THEN t.hours ELSE 0 END) AS na_hours
        FROM `tabTimesheet Detail` t
        JOIN `tabTimesheet` ts ON t.parent = ts.name
        LEFT JOIN `tabProject` p ON t.project = p.name
        LEFT JOIN `tabEmployee` e ON ts.employee = e.name
        LEFT JOIN `tabDesignation` d ON e.designation = d.name
        WHERE {conditions}
        GROUP BY ts.employee, e.employee_name
    """, tuple(query_params) if query_params else (), as_dict=True)

    for row in data:
        total = row.total_hours or 0
        total_profitable = (row.billable_hours or 0) + (row.partial_billable_hours or 0)
        row.total_profitable_hours = total_profitable
        row.profitable_ratio = round((total_profitable / total) * 100, 2) if total else 0
        row.non_billable_hours = total - total_profitable

    data.sort(key=lambda x: x.get("profitable_ratio", 0))  # sort ascending by Billable Hours %

    columns = [
        {"label": "Employee", "fieldname": "employee", "fieldtype": "Link", "options": "Employee", "width": 180},
        {"label": "Employee Name", "fieldname": "employee_name", "fieldtype": "Data", "width": 180},
        {"label": "Employment Type", "fieldname": "employment_type", "fieldtype": "Data", "width": 180},
        {"label": "Billable Hours %", "fieldname": "profitable_ratio", "fieldtype": "Percent", "width": 180},
        {"label": "Total Hours", "fieldname": "total_hours", "fieldtype": "Float", "width": 150},
        {"label": "Non-Billable Hours", "fieldname": "non_billable_hours", "fieldtype": "Float", "width": 180},
        {"label": "Total Billable Hours", "fieldname": "total_profitable_hours", "fieldtype": "Float", "width": 180},
        {"label": "Billable Hours", "fieldname": "billable_hours", "fieldtype": "Float", "width": 150},
        {"label": "Partially Billable Hours", "fieldname": "partial_billable_hours", "fieldtype": "Float", "width": 180},
        {"label": "NA Hours", "fieldname": "na_hours", "fieldtype": "Float", "width": 150},
    ]

    return columns, data
