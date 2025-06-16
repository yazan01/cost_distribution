frappe.query_reports["Partner portfolio Financial Performance"] = {
    "filters": [
        {
            "fieldname": "partner",
            "label": ("Partner"),
            "fieldtype": "Select",
            "options": [],
            "get_data": function () {
                return frappe.call({
                    method: "cost_distribution.cost_distribution.report.partner_portfolio_financial_performance.partner_portfolio_financial_performance.get_partners",
                }).then(r => {
                    const options = (r.message || []).map(p => p.name);
                    frappe.query_report.set_filter_options("partner", options);
                });
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
