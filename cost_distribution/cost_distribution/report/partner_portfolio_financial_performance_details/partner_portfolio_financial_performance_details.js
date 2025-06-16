
frappe.query_reports["Partner Portfolio Financial Performance Details"] = {
    "filters": [
        {
            "fieldname": "partner",
            "label": ("Partner"),
            "fieldtype": "Select",
            "options": [],
            "default": "",
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
            "fieldname": "data_type",
            "label": __("Data Type"),
            "fieldtype": "Select",
            "options": "CTC\nActual Cost\nRevenue\nProfit Loss CTC\nProfit Loss Actual",
            "default": "CTC",
            "on_change": function() {
                frappe.query_report.refresh();
            }
        },
        {
            "fieldname": "group",
            "label": ("Group Per Employee"),
            "fieldtype": "Check",
            "default": 0
        },
        {
            "fieldname": "from_date",
            "label": ("From Date"),
            "fieldtype": "Date",
            "on_change": function() {
                frappe.query_report.refresh();
            }
        },
        {
            "fieldname": "to_date",
            "label": ("To Date"),
            "fieldtype": "Date",
            "on_change": function() {
                frappe.query_report.refresh();
            }
        }
    ],

    onload: function (report) {
        // الحصول على الموظف الحالي
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

                // جلب قائمة الشركاء
                frappe.call({
                    method: "frappe.client.get_list",
                    args: {
                        doctype: "Employee",
                        filters: {
                            designation: ["in", ["Partner", "CEO"]]
                        },
                        fields: ["name", "employee_name"]
                    },
                    callback: function (r) {
                        if (r.message) {
                            const partner_filter = frappe.query_report.get_filter("partner");
                            let options = r.message.map(row => ({
                                label: `${row.employee_name} (${row.name})`,
                                value: row.name
                            }));

                            partner_filter.df.options = options;
                            partner_filter.refresh();

                            if (is_partner) {
                                // جعل الفلتر read-only وتعيين القيمة تلقائيًا
                                partner_filter.df.read_only = 1;
                                partner_filter.set_value(current_employee.name);
                                partner_filter.refresh();  // تحديث الحالة بعد التعديل
                            }
                        }
                    }
                });
            }
        });
    }
};
