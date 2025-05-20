frappe.query_reports["Partner portfolio Financial Performance"] = {
    "filters": [        
        {
            "fieldname": "partner",
            "label": __("Partner"),
            "fieldtype": "Link",
            "options": "Employee",
            "get_query": function() {
                return {
                    "filters": [
                        ["name", "in", (function() {
                            let partners = [];
                            frappe.call({
                                method: "frappe.client.get_list",
                                args: {
                                    doctype: "Partners Percentage",
                                    fields: ["partner"],
                                    distinct: true
                                },
                                async: false,
                                callback: function(r) {
                                    if(r.message) {
                                        partners = r.message.map(p => p.partner);
                                    }
                                }
                            });
                            return partners;
                        })()]
                    ]
                };
            },
            "on_change": function() {
                // عند تغيير الشريك، قم بتحديث خيارات المشروع
                let project_filter = frappe.query_report.get_filter('project');
                if (project_filter) project_filter.refresh();
            }
        },
        {
            "fieldname": "project_type",
            "label": __("Project Type"),
            "fieldtype": "Link",
            "options": "Project Type",
            "on_change": function() {
                // عند تغيير نوع المشروع، قم بتحديث خيارات المشروع
                let project_filter = frappe.query_report.get_filter('project');
                if (project_filter) project_filter.refresh();
            }
        },
        {
            "fieldname": "portfolio_category",
            "label": __("Portfolio Category"),
            "fieldtype": "Select",
            "options": "New\nOld",
            "default": "New"
        },
        {
            "fieldname": "project",
            "label": __("Project"),
            "fieldtype": "Table MultiSelect",
            "options": "Project",
            "get_data": function(txt) {
                // الحصول على قيم الفلاتر الأخرى
                let partner_value = frappe.query_report.get_filter_value('partner');
                let project_type_value = frappe.query_report.get_filter_value('project_type');
                
                return new Promise(function(resolve) {
                    let filters = [];
                    
                    // بناء شرط البحث عن المشاريع التي تنتمي للشريك المحدد
                    if (partner_value) {
                        frappe.call({
                            method: "frappe.client.get_list",
                            args: {
                                doctype: "Project",
                                fields: ["name", "project_name"],
                                filters: [
                                    // شرط يضمن أن المشروع يحتوي على الشريك المحدد في جدول Partners Percentage
                                    ["name", "in", (function() {
                                        let projects = [];
                                        frappe.call({
                                            method: "frappe.db.sql",
                                            args: {
                                                query: `
                                                    SELECT pp.parent 
                                                    FROM \`tabPartners Percentage\` AS pp 
                                                    JOIN \`tabProject\` AS pro 
                                                    ON pro.name = pp.parent 
                                                    WHERE pp.partner = '${partner_value}' 
                                                    ${project_type_value ? `AND pro.project_type = '${project_type_value}'` : ''}
                                                `,
                                                as_dict: 1
                                            },
                                            async: false,
                                            callback: function(r) {
                                                if(r.message) {
                                                    projects = r.message.map(p => p.parent);
                                                }
                                            }
                                        });
                                        return projects;
                                    })()]
                                ]
                            },
                            callback: function(r) {
                                let options = [];
                                if (r.message) {
                                    options = r.message.map(p => {
                                        return {
                                            value: p.name,
                                            label: `${p.name}: ${p.project_name || ''}`
                                        };
                                    });
                                }
                                resolve(options);
                            }
                        });
                    } else {
                        // إذا لم يتم تحديد شريك، قم بإرجاع مصفوفة فارغة
                        resolve([]);
                    }
                });
            }
        },
        {
            "fieldname": "view",
            "label": __("View"),
            "fieldtype": "Select",
            "options": "Year\nMonth",
            "default": "Year"
        },
        {
            "fieldname": "aggregated",
            "label": __("Aggregated"),
            "fieldtype": "Check",
            "default": 0
        }
    ]
};