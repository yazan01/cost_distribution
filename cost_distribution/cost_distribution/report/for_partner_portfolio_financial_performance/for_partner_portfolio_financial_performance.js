frappe.query_reports["For Partner portfolio Financial Performance"] = {
    "filters": [
        {
            "fieldname": "partner",
            "label": ("Partner"),
            "fieldtype": "Select",
            "options": [],
            "default": "",
            "read_only": 0,
            "on_change": function() {
                // تفريغ فلتر المشاريع عند تغيير البارتنر
                const project_filter = frappe.query_report.get_filter("project");
                if (project_filter) {
                    project_filter.set_value([]);
                }
                
                // تفريغ فلتر نوع المشروع عند تغيير البارتنر
                const project_type_filter = frappe.query_report.get_filter("project_type");
                if (project_type_filter) {
                    project_type_filter.set_value([]);
                }
                
                // تفريغ فلتر فئة المحفظة عند تغيير البارتنر
                const portfolio_category_filter = frappe.query_report.get_filter("portfolio_category");
                if (portfolio_category_filter) {
                    portfolio_category_filter.set_value([]);
                }
                
                frappe.query_report.refresh();
            }
        },
        {
            "fieldname": "project_type",
            "label": ("Project Type"),
            "fieldtype": "MultiSelectList",
            "get_data": function(txt) {
                return frappe.db.get_link_options('Project Type', txt);
            },
            "on_change": function() {
                // تفريغ فلتر المشاريع عند تغيير نوع المشروع
                const project_filter = frappe.query_report.get_filter("project");
                if (project_filter) {
                    project_filter.set_value([]);
                    frappe.query_report.refresh();
                }
            }
        },
        {
            "fieldname": "portfolio_category",
            "label": ("Portfolio Category"),
            "fieldtype": "MultiSelectList",
            "get_data": function(txt) {
                return frappe.db.get_link_options('Portfolio Category', txt);
            },
            "on_change": function() {
                // تفريغ فلتر المشاريع عند تغيير فئة المحفظة
                const project_filter = frappe.query_report.get_filter("project");
                if (project_filter) {
                    project_filter.set_value([]);
                    frappe.query_report.refresh();
                }
            }
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
                    method: "cost_distribution.cost_distribution.report.for_partner_portfolio_financial_performance.for_partner_portfolio_financial_performance.get_projects_by_partner",
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
        },
        {
            "fieldname": "persentage",
            "label": ("Partner Persentage"),
            "fieldtype": "Check",
            "default": 1
        }
    ],

    onload: function (report) {
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
                const current_employee = res.message && res.message[0];
                const is_partner = current_employee && current_employee.designation === "Partner";
    
                // استدعاء الدالة المخصصة بدل get_list
                frappe.call({
                    method: "cost_distribution.cost_distribution.report.for_partner_portfolio_financial_performance.for_partner_portfolio_financial_performance.get_partner_list",
                    callback: function (r) {
                        const partner_filter = frappe.query_report.get_filter("partner");
                        let options = r.message.map(row => ({
                            label: `${row.employee_name} (${row.name})`,
                            value: row.name
                        }));
    
                        partner_filter.df.options = options;
                        partner_filter.refresh();
    
                        if (is_partner) {
                            partner_filter.df.read_only = 1;
                            partner_filter.set_value(current_employee.name);
                            partner_filter.refresh();
                        }
                    }
                });
            }
        });
    }
    
};
