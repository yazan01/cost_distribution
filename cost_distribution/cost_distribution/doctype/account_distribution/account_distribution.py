# Copyright (c) 2024, Furqan Asghar and contributors
# For license information, please see license.txt

from frappe.model.document import Document
import frappe
from frappe import _
from frappe.utils import flt, cstr


class AccountDistribution(Document):
    def validate(self):
        """Validates and processes salary slips and costing summary."""
        self.validate_fields()
        self.set_salary_slip_and_rate1()
        self.create_costing_summary()

    def on_submit(self):
        """Handles actions upon submitting the document."""
        if not self.journal_entry:
            frappe.throw(_('No Journal Entry linked.'))

        jv = frappe.get_doc('Journal Entry', self.journal_entry)
        if jv.docstatus != 1:
            jv.submit()

    def on_cancel(self):
        """Handles actions upon canceling the document."""
        if self.journal_entry:
            jv = frappe.get_doc('Journal Entry', self.journal_entry)
            if jv.docstatus == 1:
                jv.cancel()

    def validate_fields(self):
        """Validates required fields for account distribution."""
        required_fields = {
            "Company": self.company,
            "Account": self.account,
            "Start Date": self.from_date,
            "End Date": self.to_date,
        }
        missing_fields = [field for field, value in required_fields.items() if not value]
        if missing_fields:
            frappe.throw(_("Please set the following fields: {0}").format(", ".join(missing_fields)))

        

    def set_salary_slip_and_rate1(self):
        """Fetches and sets salary slip data based on account distribution type."""
        if self.distribution_type == 'Account Distribution':
            self.employee_account_data = []

            result = frappe.db.sql(
                """
                SELECT 
                    gle.party AS employee, 
                    emp.employee_name, 
                    COALESCE(ts.total_hours, 0) AS total_hours, 
                    gle.debit,
                    gle.credit
                FROM 
                    (SELECT 
                        party, 
                        SUM(debit) AS debit,
                        SUM(credit) AS credit
                     FROM 
                        `tabGL Entry`
                     WHERE 
                        docstatus = 1
                        AND is_cancelled = 0
                        AND posting_date BETWEEN %s AND %s
                        AND party_type = 'Employee'
                        AND company = %s
                        AND account = %s
                     GROUP BY 
                        party
                    ) AS gle
                LEFT JOIN 
                    `tabEmployee` AS emp
                ON 
                    gle.party = emp.name
                LEFT JOIN 
                    (SELECT 
                        employee, 
                        SUM(total_hours) AS total_hours 
                     FROM 
                        `tabTimesheet`
                     WHERE 
                        docstatus = 1
                        AND start_date >= %s
                        AND end_date <= %s
                     GROUP BY 
                        employee
                    ) AS ts
                ON 
                    emp.name = ts.employee;
            """,
                (self.from_date, self.to_date, self.company, self.account, self.from_date, self.to_date), as_dict=True,
            )
            if not result:
                frappe.throw(_("No Employee in This Account"))
		
            for row in result:
                if (flt(row.get('debit')) - flt(row.get('credit'))) != 0:
                    self.append('employee_account_data', {
                        'employee': row.get('employee'),
                        'employee_name': row.get('employee_name'),
                        'total': flt(row.get('debit')) - flt(row.get('credit')),
                        'total_hours': row.get('total_hours'),
                    })
            

    def create_costing_summary(self):
        """Creates a costing summary for the document."""
        if self.distribution_type not in ['Employee', 'Account Distribution']:
            return

        self.costing_summary = []
        total_cost_of_project = 0

        for salary_data in self.employee_account_data:
            time_sheet_summary = get_time_sheet_summary(salary_data, self)
            if time_sheet_summary:
                if "employee_with_no_timesheet" in time_sheet_summary:
                    self.append(
                        "employee_with_no_timesheet",
                        {"employee": time_sheet_summary["employee_with_no_timesheet"]}
                    )
                elif "project_list" in time_sheet_summary:
                    for project in time_sheet_summary["project_list"]:
                        self.append('costing_summary', {
                            'project': project.project,
                            'employee': salary_data.employee,
                            'cost_center': project.cost_center,
                            'cost_per_hour': project.cost_per_hour,
                            'total_hours': project.total_hours,
                            'gosi_amount': project.gosi_amount,
                            'total_cost_of_project': project.total_cost_of_project,
                            'perc_distribution': project.perc_distribution,
                            'timesheets_data': project.timesheets_data,
                        })
                        total_cost_of_project += project.total_cost_of_project

        self.amount = total_cost_of_project

    @frappe.whitelist()
    def create_journal_entry(self):
        self.validate()
        precision = frappe.get_precision("Journal Entry Account", "debit_in_account_currency")
        jv = frappe.new_doc("Journal Entry")
        jv.company = self.company
        jv.posting_date = self.posting_date
        jv.user_remark = 'JV Created VIA {0}'.format(frappe.get_desk_link('Cost Distribution', self.name))

        jv.append('accounts', {
			'account': self.credit_account,
			'credit_in_account_currency': flt(self.amount, precision),
            		'cost_center': self.default_cost_center
		})

        if not self.costing_summary:
            frappe.throw('Costing Summary Table is Empty')

        gosi_debit_sum = 0
        if self.distribution_type in ['Employee', 'Account Distribution']:
            for d in self.costing_summary:
                d.debit = flt(d.total_cost_of_project, precision)

            for d in self.costing_summary:
                d.gosi_debit = flt(d.gosi_amount, precision)

            gosi_debit_sum = sum([d.gosi_debit for d in self.costing_summary])

            gosi_debit_sum = sum([d.gosi_debit for d in self.costing_summary])
		

		##### if there's rounding difference in debit then appending in last row
        diff = self.amount - sum([d.debit for d in self.costing_summary]) - gosi_debit_sum
        if diff:
            for d in self.costing_summary:
                if d.idx == len(self.costing_summary):
                    d.debit += diff

        for d in self.costing_summary:
            jv.append('accounts', {
				'party': d.employee if self.distribution_type in ['Employee', 'Account Distribution'] else None,
				'party_type': 'Employee' if self.distribution_type in ['Employee', 'Account Distribution'] else None,
				'project': d.project,
				'cost_center': d.cost_center,
				'account': self.debit_account,
				'debit_in_account_currency': d.debit
			})

            if d.gosi_amount and self.distribution_type in ['Employee', 'Account Distribution']:
                jv.append('accounts', {
					'party': d.employee if self.distribution_type in ['Employee', 'Account Distribution'] else None,
					'party_type': 'Employee' if self.distribution_type in ['Employee', 'Account Distribution'] else None,
					'project': d.project,
					'cost_center': d.cost_center,
					'account': self.gosi_debit_account,
					'debit_in_account_currency': d.gosi_debit
				})

        jv.save()
        self.db_set('journal_entry', jv.name)


@frappe.whitelist()
def get_time_sheet_summary(salary_data, cost_dist_doc):
	employee = salary_data.employee
	total = salary_data.total
	from_date = cost_dist_doc.from_date
	to_date = cost_dist_doc.to_date
	default_cost_center = cost_dist_doc.default_cost_center

	from_date_1 = str(from_date)+" 00:00:01.000"
	to_date_1 = str(to_date)+" 23:59:59.995"

	data = frappe.db.sql(
		"""SELECT ts.name as timesheet, tsd.project, tsd.from_time, tsd.to_time, tsd.hours, tsd.name  as timesheet_child
		FROM `tabTimesheet` ts , `tabTimesheet Detail` tsd 
		WHERE ts.docstatus=1 AND ts.name = tsd.parent AND ts.employee=%s AND ts.docstatus=1 AND 
		tsd.from_time>=%s AND tsd.to_time<=%s""",
		(employee, from_date_1, to_date_1), as_dict=True,
	)
	if not data:
		frappe.msgprint("Employee With No Timesheet")
		return {"employee_with_no_timesheet": employee}

	hours = sum([d.hours for d in data])
	net_rate_per_hour = total / hours
	

	data_dict = frappe._dict()
	for d in data:
		data_dict.setdefault(d.project, {
			'total_hours': 0, 'total_cost_of_project': 0, 'gosi_amount': 0, 'cost_per_hour': net_rate_per_hour, 'timesheets_data': []
		})

		data_dict[d.project]['total_hours'] += d.hours
		data_dict[d.project]['timesheets_data'].append({'timesheet': d.timesheet, 'timesheet_child': d.timesheet_child, 'hours': d.hours})

	total_cost_of_all_projects = 0
	for d in data_dict:
		# data_dict[d]['gosi_amount'] = data_dict[d]['total_hours'] * gosi_amount_per_hour
		data_dict[d]['total_cost_of_project'] = data_dict[d]['total_hours'] * net_rate_per_hour
		total_cost_of_all_projects += data_dict[d]['total_cost_of_project']

	project_list = []
	for k, v in data_dict.items():
		project_list.append(frappe._dict({
			'project': k, 
			'cost_per_hour': net_rate_per_hour,
			'total_hours': data_dict[k]['total_hours'], 
			'gosi_amount': data_dict[k]['gosi_amount'],
			'timesheets_data': cstr(data_dict[k]['timesheets_data']),
			'total_cost_of_project': data_dict[k]['total_cost_of_project'],
			'perc_distribution': (data_dict[k]['total_cost_of_project'] / (total_cost_of_all_projects or 1)) * 100
		}))

	
	#for d in project_list:
		#if d.get('project'):
			#d['cost_center'] = frappe.get_cached_value('Project', d.get('project'), 'cost_center')
		#else:
			#d['cost_center'] = default_cost_center

	companyofpayroll = frappe.get_value("Account", cost_dist_doc.account, "company")
	for d in project_list:
		if d.get('project'):
			cost_center = frappe.get_cached_value('Project', d.get('project'), 'cost_center')
		else:
			cost_center = default_cost_center
		last_dash_index = cost_center.rfind('-')
		if last_dash_index != -1:
			cost_center = cost_center[:last_dash_index].strip()
		if companyofpayroll == "iValueJOR":
			cost_center += " - iJOR"
		elif companyofpayroll == "iValueUAE":
			cost_center += " - iUAE"
		elif companyofpayroll == "iValue KSA":
			cost_center += " - iKSA"
		else:
			cost_center += " - iV"
		d['cost_center'] = cost_center


	##### if there's rounding difference then appending in last project
	if project_list:
		diff = 100 - sum([d.perc_distribution for d in project_list])
		if diff:
			project_list[-1]['perc_distribution'] += diff

	return {"project_list": project_list}
