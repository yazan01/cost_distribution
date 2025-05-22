
frappe.query_reports["Partner Portfolio Financial Performance Details"] = {
    "filters": [
        {
            "fieldname": "partner",
            "label": ("Partner"),
            "fieldtype": "Link",
            "options": "Employee",
            "get_query": function() {
                return {
                    "filters": [
                        ["designation", "in", ["Partner", "CEO"]]
                    ]
                };
            }
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
            "label": __("Project"),
            "fieldtype": "MultiSelectList",
            "get_data": function (txt) {
                const partner = frappe.query_report.get_filter_value("partner");
                const project_type = frappe.query_report.get_filter_value("project_type");
                const portfolio_category = frappe.query_report.get_filter_value("portfolio_category");
        
                if (!partner) {
                    frappe.msgprint("Please select a Partner first");
                    return [];
                }
        
                return frappe.call({
                    method: "cost_distribution.cost_distribution.report.partner_portfolio_financial_performance.partner_portfolio_financial_performance.get_projects_by_partner",
                    args: {
                        partner: partner,
                        txt: txt || "",
                        project_type: project_type || null,
                        portfolio_category: portfolio_category || null
                    },
                }).then(r => {
                    return r.message || [];
                });
            }
        },
        {
            "fieldname": "data_type",
            "label": __("Data Type"),
            "fieldtype": "Select",
            "options": "\nCTC\nActual Cost\nRevenue\nProfit Loss CTC\nProfit Loss Actual",
            "default": "CTC",
            "on_change": function() {
                frappe.query_report.refresh();
            }
        },
        {
            "fieldname": "from_date",
            "label": ("From Date"),
            "fieldtype": "Date"
        },
        {
            "fieldname": "to_date",
            "label": ("To Date"),
            "fieldtype": "Date"
        },
        {
            "fieldname": "aggregated",
            "label": ("Aggregated"),
            "fieldtype": "Check",
            "default": 0
        }
    ]
};