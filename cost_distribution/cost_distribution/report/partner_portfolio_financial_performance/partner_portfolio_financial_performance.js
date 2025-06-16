frappe.query_reports["Partner portfolio Financial Performance"] = {
    "filters": [
        {
            "fieldname": "partner",
            "label": ("Partner"),
            "fieldtype": "Select",
            "options": [],
            "read_only": 0
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
    ],

    onload: function (report) {
        // أولاً، نحصل على الموظف المرتبط بالمستخدم الحالي
        frappe.call({
            method: "frappe.client.get_list",
            args: {
                doctype: "Employee",
                filters: {
                    user_id: frappe.session.user
                },
                fields: ["name", "employee_name", "designation"]
            },
            callback: function (res) {
                let current_employee = res.message && res.message[0];
                let is_partner = current_employee && current_employee.designation === "Partner";

                // تحميل الشركاء
                frappe.call({
                    method: "frappe.client.get_list",
                    args: {
                        doctype: "Employee",
                        filters: {
                            designation: ["in", ["Partner", "CEO"]]
                        },
                        fields: ["name", "employee_name"],
                        limit_page_length: 100
                    },
                    callback: function (r) {
                        if (r.message) {
                            const partner_filter = frappe.query_report.get_filter("partner");
                            let options = [];

                            r.message.forEach(row => {
                                options.push({
                                    label: `${row.employee_name} (${row.name})`,
                                    value: row.name
                                });
                            });

                            partner_filter.df.options = options;
                            partner_filter.refresh();

                            if (is_partner) {
                                // تعبئة الفلتر باسم الموظف الحالي وقفل الفلتر
                                partner_filter.set_value(current_employee.name);
                                partner_filter.toggle_enable(false); // make it read-only
                            }
                        }
                    }
                });
            }
        });
    }
    
};
