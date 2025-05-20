frappe.query_reports["CTC"] = {
	"filters": [
		{
			"fieldname": "from_date",
			"label": __("From Date"),
			"fieldtype": "Date",
			"default": '2023-01-01',
			"reqd": 1,
			"width": "60px"
		},
		{
			"fieldname": "to_date",
			"label": __("To Date"),
			"fieldtype": "Date",
			"default": frappe.datetime.get_today(),
			"reqd": 1,
			"width": "60px"
		},
		{
			"fieldname": "project",
			"label": __("Project"),
			"fieldtype": "MultiSelectList",
			get_data: function(txt) {
				return frappe.db.get_link_options('Project', txt);
			}
		},
		{
			"fieldname": "partner",
			"label": __("Manager"),
			"fieldtype": "Link",
			"options": "Employee",
			get_data: function(txt) {
				return frappe.db.get_list('Employee', {
					fields: ['name', 'employee_name'],
					filters: {designation: 'Partner'}
				}).then(function(results) {
					// Format the results as an array of {value, label} objects
					let partners = results.map(function(employee) {
						return {
							"value": employee.name,
							"label": employee.employee_name
						};
					});
					return partners;
				});
			}
		},
		{
			"fieldname": "project_type",
			"label": __("Project Type"),
			"fieldtype": "Link",
			"options": "Project Type"
		},
		{
			"fieldname": "Assign_to",
			"label": __("Assign To"),
			"fieldtype": "Link",
			"options": "Employee",
			get_data: function(txt) {
				return frappe.db.get_list('Employee', {
					fields: ['name', 'employee_name'],
					filters: {designation: 'Partner'}
				}).then(function(results) {
					// Format the results as an array of {value, label} objects
					let partners = results.map(function(employee) {
						return {
							"value": employee.name,
							"label": employee.employee_name
						};
					});
					return partners;
				});
			}
		},
		{
			"fieldname": "group_by_project",
			"label": __("Group by Project"),
			"fieldtype": "Check",
			"default": 0
		},
		{
			"fieldname": "revenue",
			"label": __("Revenue"),
			"fieldtype": "Check",
			"default": 0
		},
		{
			"fieldname": "indirect_costs",
			"label": __("InDirect Costs"),
			"fieldtype": "Check",
			"default": 0
		},
		{
			"fieldname": "ctc",
			"label": __("CTC"),
			"fieldtype": "Check",
			"default": 0
		}
	]
};
