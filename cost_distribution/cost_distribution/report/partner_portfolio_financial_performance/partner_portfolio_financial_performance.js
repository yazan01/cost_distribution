frappe.query_reports["Partner portfolio Financial Performance"] = {
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
                if (!partner) {
                    frappe.msgprint("Please select a Partner first");
                    return [];
                }
        
                return frappe.call({
                    method: "frappe.client.get_list",
                    args: {
                        doctype: "Partners Percentage",
                        fields: ["parent"],
                        filters: {
                            partner: partner,
                            parent: ["like", "%" + txt + "%"]
                        },
                        limit_page_length: 50
                    },
                    callback: function(r) {
                        if (r.message) {
                            const options = r.message.map(d => ({
                                value: d.parent,
                                description: d.parent
                            }));
                            frappe.query_report.set_filter_options("project", options);
                        }
                    }
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
