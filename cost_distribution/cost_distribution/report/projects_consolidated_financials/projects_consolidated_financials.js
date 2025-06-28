frappe.query_reports["Projects Consolidated Financials"] = {
	"filters": [		
		{
			"fieldname": "project",
			"label": __("Project"),
			"fieldtype": "Link",
			"options": "Project"
		},
		{
			"fieldname": "partner",
			"label": __("Project Manager"),
			"fieldtype": "Select",
			"options": [],
			"default": "",
			"reqd": 0
		},
		{
			"fieldname": "project_type",
			"label": __("Project Type"),
			"fieldtype": "Link",
			"options": "Project Type"
		},
		{
			"fieldname": "customer",
			"label": __("Client"),
			"fieldtype": "Link",
			"options": "Customer"
		},
		{ 
			"fieldname": "status", 
			"label": __("Status"), 
			"fieldtype": "Select", 
			"options": ["", "Open", "Completed", "Cancelled"],
			"default": "" 
		}
	],

	
	formatter: function(value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);

		if ((column.fieldtype === "Float" || column.fieldtype === "Currency") && data && data.project_id) {		
			value = `<span class="currency-cell"
				data-column="${column.fieldname}"
				data-project="${data.project_id}"
				title="Click to view ${column.label} details">${value}</span>`;
		}

		return value;
	},

	onload: function(report) {
		// تحميل بيانات الموظف الحالي
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
				const is_partner = current_employee && ["Partner"].includes(current_employee.designation);

				// تحميل قائمة الشركاء من السيرفر
				frappe.call({
					method: "cost_distribution.cost_distribution.report.projects_consolidated_financials.projects_consolidated_financials.get_partner_list",
					callback: function (r) {
						const partner_filter = frappe.query_report.get_filter("partner");
						if (r.message) {
							let options = r.message.map(emp => ({
								label: `${emp.employee_name} (${emp.name})`,
								value: emp.name
							}));
							partner_filter.df.options = options;

							// تعبئة الفلتر تلقائيًا إذا كان المستخدم Partner
							if (is_partner) {
								partner_filter.df.read_only = 1;
								partner_filter.set_value(current_employee.name);
							}
							partner_filter.refresh();
						}
					}
				});
			}
		});
		
		// Add click event
		report.page.wrapper.on('click', '.currency-cell', function () {
			const columnName = $(this).data('column');
			const projectId = $(this).data('project');

			console.log("Clicked cell:", { columnName, projectId });

			// Set from_date and to_date based on column name
			let fromDate, toDate;
			if (columnName.includes('2023')) {
				fromDate = '2023-01-01';
				toDate = '2023-12-31';
			} else if (columnName.includes('2024')) {
				fromDate = '2024-01-01';
				toDate = '2024-12-31';
			} else if (columnName.includes('2025')) {
				fromDate = '2025-01-01';
				toDate = '2025-12-31';
			} else {
				// Default if no specific year
				fromDate = '2023-01-01';
				toDate = frappe.datetime.get_today();
			}

			let reporttype;
			if (columnName.includes('profit_loss_ctc')) {
				reporttype = 'Profit Loss CTC';
			} else if (columnName.includes('profit_loss_actual')) {
				reporttype = 'Profit Loss Actual';
			} else if (columnName.includes('actual')) {
				reporttype = 'Actual Cost';
			} else if (columnName.includes('revenue')) {
				reporttype = 'Revenue';
			} else {
				reporttype = 'CTC';
			}

			// Create URL with parameters
			let url = '/app/query-report/Project Financial Details?';
			url += `project=${encodeURIComponent(projectId)}`;
			url += `&data_type=${encodeURIComponent(reporttype)}`;
			url += `&from_date=${encodeURIComponent(fromDate)}`;
			url += `&to_date=${encodeURIComponent(toDate)}`;
			
			// Open in new tab
			window.open(url, '_blank');
		});

		// Add styling
		const style = document.createElement("style");
		style.innerHTML = `
			.report-table tbody tr:hover {
				background-color: #000000;
				cursor: pointer;
			}
			.currency-cell {
				font-weight: bold;
				color: #000000;
			}
			.currency-cell:hover {
				text-decoration: underline;
			}
			.report-wrapper .report-table {
				display: block;
				overflow-x: auto;
			}
		`;
		document.head.appendChild(style);
	}

};
