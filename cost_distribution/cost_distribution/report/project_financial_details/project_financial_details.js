frappe.query_reports["Project Financial Details"] = {
    "filters": [
        {
            "fieldname": "project",
            "label": __("Project"),
            "fieldtype": "Link",
            "options": "Project",
            "reqd": 1,
            "on_change": function() {
                var project = frappe.query_report.get_filter_value('project');
                if (project) {
                    frappe.db.get_value('Project', project, 'project_name', function(data) {
                        updateProjectNameDisplay(data.project_name);
                    });
                } else {
                    updateProjectNameDisplay('');
                }
                
                frappe.query_report.refresh();
            }
        },
        {
            "fieldname": "data_type",
            "label": __("Data Type"),
            "fieldtype": "Select",
            "options": "\nCTC\nActual Cost\nRevenue\nProfit Loss CTC\nProfit Loss Actual",
            "default": "",
            "on_change": function() {
                frappe.query_report.refresh();
            }
        },
        {
            "fieldname": "from_date",
            "label": __("From Date"),
            "fieldtype": "Date",
            "on_change": function() {
                frappe.query_report.refresh();
            }
        },
        {
            "fieldname": "to_date",
            "label": __("To Date"),
            "fieldtype": "Date",
            "on_change": function() {
                frappe.query_report.refresh();
            }
        }
    ],
    
    "onload": function(report) {
        $(frappe.query_report.page.page_form).after(
            '<div id="project_name_display" style="margin: 10px 0px; padding: 8px 15px; border-left: 3px solid #5e64ff; background-color: #f9f9f9; font-weight: bold; display: none;">' +
            '<span>Project Name: <span id="project_name_text"></span></span>' +
            '</div>'
        );
        
        let project = frappe.query_report.get_filter_value('project');
        if (project) {
            frappe.db.get_value('Project', project, 'project_name', function(data) {
                updateProjectNameDisplay(data.project_name);
            });
        }
    }
};

function updateProjectNameDisplay(projectName) {
    if (projectName && projectName.trim() !== '') {
        $('#project_name_text').text(projectName);
        $('#project_name_display').show();
    } else {
        $('#project_name_display').hide();
    }
}
