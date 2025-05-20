frappe.query_reports["Partner portfolio Financial Performance"] = {
    "filters": [        
        {
            "fieldname": "partner",
            "label": ("Partner"),
            "fieldtype": "Link",
            "options": "Employee",
        },
        {
            "fieldname": "project_type",
            "label": ("Project Type"),
            "fieldtype": "Link",
            "options": "Project Type"
        },
        {
            "fieldname": "portfolio_category",
            "label": ("Portfolio Category"),
            "fieldtype": "Select",
            "options": "New\nOld",
            "default": "New"
        },
        {
            "fieldname": "project",
            "label": ("Project"),
            "fieldtype": "Link",
            "options": "Project"
        },
        {
            "fieldname": "view",
            "label": ("View"),
            "fieldtype": "Select",
            "options": "Year\nMonth",
            "default": "Year"
        },
        {
            "fieldname": "aggregated",
            "label": ("Aggregated"),
            "fieldtype": "Check",
            "default": 0
        }
    ]

};
