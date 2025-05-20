# Copyright (c) 2023, Furqan Asghar and contributors
# For license information, please see license.txt

from frappe.model.document import Document
import frappe
from frappe import _
from frappe.utils import flt, cstr, cint

class CostDistribution(Document):
	def validate(self):
		self.set_salary_slip_and_rate1()
		# self.set_salary_slip_and_rate()
		self.create_costing_summary()
		# self.remove_employees_with_no_hours()
		self.validate_costing_summary()
		# self.validate_total_hours()
		self.check_duplicate()

	def on_submit(self):
		if self.journal_entry:
			jv = frappe.get_doc('Journal Entry', self.journal_entry)
			jv.submit()
		else:
			frappe.throw(_('Not Journal Entry linked.'))

	def on_cancel(self):
		if self.journal_entry:
			jv = frappe.get_doc('Journal Entry', self.journal_entry)
			if jv.docstatus==1:
				jv.cancel()

	def set_salary_slip_and_rate1(self):
		if self.distribution_type in ['Employee', 'All Employee']:
			if not self.payroll_entry:
				frappe.throw(_("Please set Payroll Entry"))
			
			if self.distribution_type == 'Employee' and self.employee:
				self.employee_salary_data = []
				salary_slip_data = get_salary_slip_and_rate_1(self.payroll_entry, self.employee)
				self.append('employee_salary_data', {
					'employee': self.employee,
					'employee_name': frappe.get_cached_value("Employee", self.employee, 'employee_name'),
					'salary_slip': salary_slip_data.get('salary_slip'),
					'rate_per_hour': salary_slip_data.get('rate_per_hour'),
					'gross_pay': salary_slip_data.get('gross_pay'),
					'payment_days': salary_slip_data.get('payment_days')
				})

			elif self.distribution_type == 'All Employee':
				payroll_entry = frappe.get_doc("Payroll Entry", self.payroll_entry)
				self.employee_salary_data = []
				for employee in payroll_entry.employees:
					salary_slip_data = get_salary_slip_and_rate_1(self.payroll_entry, employee.employee)
					self.append('employee_salary_data', {
						'employee': employee.employee,
						'employee_name': employee.employee_name,
						'salary_slip': salary_slip_data.get('salary_slip'),
						'rate_per_hour': salary_slip_data.get('rate_per_hour'),
						'gross_pay': salary_slip_data.get('gross_pay'),
						'payment_days': salary_slip_data.get('payment_days')
					})


	def set_salary_slip_and_rate(self):
		if self.distribution_type in ['Employee', 'All Employee'] and self.from_date and self.to_date:
			self.employee_salary_data = []
			if self.distribution_type == 'Employee' and self.employee:
				salary_slip_data = get_salary_slip_and_rate(self.employee, self.from_date, self.to_date)
				if salary_slip_data:
					# gosi_component_amount = get_gosi_component_amount(self.company, salary_slip_data.get('salary_slip'))
					self.append('employee_salary_data', {
						'employee': self.employee,
						'employee_name': self.employee_name,
						'salary_slip': salary_slip_data.get('salary_slip'),
						'rate_per_hour': salary_slip_data.get('rate_per_hour'),
						'gross_pay': salary_slip_data.get('gross_pay'),
						# 'gosi_amount': gosi_component_amount,
						# 'total_pay': salary_slip_data.get('net_pay') + gosi_component_amount,
						'payment_days': salary_slip_data.get('payment_days')
					})


			elif self.distribution_type == 'All Employee':
				employees = frappe.get_all('Employee', fields=['name', 'employee_name'], filters = {'status': 'Active', 'company': self.company})
				self.employee_with_no_timesheet = []
				for employee in employees:
					salary_slip_data = get_salary_slip_and_rate(employee.name, self.from_date, self.to_date)
					if salary_slip_data:
						if salary_slip_data.get('employee_with_no_timesheet'):
							# frappe.msgprint(cstr(salary_slip_data))
							self.append("employee_with_no_timesheet", {"employee": salary_slip_data.get('employee_with_no_timesheet')})
						else:
							# gosi_component_amount = get_gosi_component_amount(self.company, salary_slip_data.get('salary_slip'))
							self.append('employee_salary_data', {
								'employee': employee.name,
								'employee_name': employee.employee_name,
								'salary_slip': salary_slip_data.get('salary_slip'),
								'rate_per_hour': salary_slip_data.get('rate_per_hour'),
								'gross_pay': salary_slip_data.get('gross_pay'),
								# 'gosi_amount': gosi_component_amount,
								# 'total_pay': salary_slip_data.get('net_pay') + gosi_component_amount,
								'payment_days': salary_slip_data.get('payment_days')
							})


	def create_costing_summary(self):
		if self.distribution_type in ['Employee', 'All Employee']:
			self.costing_summary = []
			total_cost_of_project = 0
			for salary_data in self.employee_salary_data:
				time_sheet_summary = get_time_sheet_summary(salary_data, self)
				if time_sheet_summary:
					if time_sheet_summary.get("employee_with_no_timesheet"):
						self.append("employee_with_no_timesheet", {"employee": time_sheet_summary.get('employee_with_no_timesheet')})
					
					elif time_sheet_summary.get("project_list"):
						total_hours = 0
						total_cost_of_project += salary_data.gross_pay
						for project in time_sheet_summary.get("project_list"):
							total_hours += project.total_hours
							self.append('costing_summary', {
							'project': project.project,
							'employee': salary_data.employee,
							'cost_center': project.cost_center,
							'cost_per_hour': project.cost_per_hour,
							'total_hours': project.total_hours,
							'gosi_amount': project.gosi_amount,
							'total_cost_of_project': project.total_cost_of_project,
							'perc_distribution': project.perc_distribution,
							'timesheets_data': project.timesheets_data
							})
							# total_cost_of_project += project.total_cost_of_project
						salary_data.total_hours = total_hours

			self.amount = total_cost_of_project

		elif self.distribution_type == 'Project':
			self.costing_summary = [d for d in self.costing_summary if d.project]

			for d in self.costing_summary:
				if not d.total_cost_of_project:
					frappe.throw(_('Project Cost missing in Row {}').format(d.idx))
			total_cost_of_all_projects = sum([d.total_cost_of_project for d in self.costing_summary])
			for d in self.costing_summary:
				d.perc_distribution = (d.total_cost_of_project / total_cost_of_all_projects) * 100

	def remove_employees_with_no_hours(self):
		to_remove = [d for d in self.employee_salary_data if not d.total_hours ]
		for d in to_remove:
			self.remove(d)

	def validate_costing_summary(self):
		# if self.distribution_type != 'Manual':
		# 	perc_distribution = 0
		# 	for d in self.costing_summary:
		# 		perc_distribution += d.perc_distribution

		# 	if perc_distribution != 100:
		# 		frappe.throw(_('Cost Distribution Percentage should be 100%'))

		if self.distribution_type == 'Manual':
			total_cost_of_projects = sum([d.total_cost_of_project for d in self.costing_summary])
			if self.amount != total_cost_of_projects:
				frappe.throw(_('In manual distribution total project cost {0} should be equal to {1} debit amount').format(total_cost_of_projects, self.amount))

	def validate_total_hours(self):
		if self.distribution_type in ['Employee', 'All Employee']:
			for data in self.employee_salary_data:
				employee_min_max_hours = frappe.db.get_value('Employee', data.employee, ['min_monthly_hours', 'max_monthly_hours'])
				min_monthly_hours = employee_min_max_hours[0]
				max_monthly_hours = employee_min_max_hours[1]

				if not min_monthly_hours:
					employee = frappe.get_desk_link('Employee', data.employee)
					frappe.throw(_('Please set minimum monthly hours for {0}').format(employee))

				if not max_monthly_hours:
					employee = frappe.get_desk_link('Employee', data.employee)
					frappe.throw(_('Please set miximum monthly hours for {0}').format(employee))

				if data.total_hours > max_monthly_hours or data.total_hours < min_monthly_hours:
					frappe.throw(_('Total hours {0} cannot be less then {1}, and cannot exceed Max hours {2} ').format(data.total_hours, min_monthly_hours, max_monthly_hours))

	def check_duplicate(self):
		if self.distribution_type not in ['Employee', 'All Employee']:
			return

		for data in self.employee_salary_data:
			filters = {'docstatus': 1, 'employee': data.employee, 'salary_slip': data.salary_slip}
			if not self.is_new():
				filters['parent'] = ['!=', self.name]

			existing_distribution = frappe.db.exists("Employee Cost Table", filters)
			if existing_distribution:
				existing_distribution = frappe.db.get_value("Employee Cost Table", existing_distribution, 'parent')
				frappe.throw(_('{0} of {1} for <b>{2}</b> is already submitted').format(
					frappe.get_desk_link("Cost Distribution", existing_distribution),
					frappe.get_desk_link("Employee", data.employee), self.month)
				)

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
			'credit_in_account_currency': flt(self.amount, precision)
		})

		# for d in self.costing_summary:
		# 	d.credit = flt(d.total_cost_of_project, precision) if self.distribution_type == 'Manual' else flt((self.amount * d.perc_distribution)/100, precision)

		if not self.costing_summary:
			frappe.throw('Costing Summary Table is Empty')

		gosi_debit_sum = 0
		if self.distribution_type in ['Employee', 'All Employee']:
			for d in self.costing_summary:
				d.debit = flt(d.total_cost_of_project, precision)

			for d in self.costing_summary:
				d.gosi_debit = flt(d.gosi_amount, precision)

			gosi_debit_sum = sum([d.gosi_debit for d in self.costing_summary])
		
		if self.distribution_type == 'Project':
			for d in self.costing_summary:
				d.debit = flt((self.amount * d.perc_distribution)/100, precision)

		if self.distribution_type == 'Manual':
			for d in self.costing_summary:
				d.debit = flt(d.total_cost_of_project, precision)

		##### if there's rounding difference in debit then appending in last row
		diff = self.amount - sum([d.debit for d in self.costing_summary]) - gosi_debit_sum
		if diff:
			for d in self.costing_summary:
				if d.idx == len(self.costing_summary):
					d.debit += diff

		for d in self.costing_summary:
			jv.append('accounts', {
				'party': d.employee if self.distribution_type in ['Employee', 'All Employee'] else None,
				'party_type': 'Employee' if self.distribution_type in ['Employee', 'All Employee'] else None,
				'project': d.project,
				'cost_center': d.cost_center,
				'account': self.debit_account,
				'debit_in_account_currency': d.debit
			})

			if d.gosi_amount and self.distribution_type in ['Employee', 'All Employee']:
				jv.append('accounts', {
					'party': d.employee if self.distribution_type in ['Employee', 'All Employee'] else None,
					'party_type': 'Employee' if self.distribution_type in ['Employee', 'All Employee'] else None,
					'project': d.project,
					'cost_center': d.cost_center,
					'account': self.gosi_debit_account,
					'debit_in_account_currency': d.gosi_debit
				})

		jv.save()
		self.db_set('journal_entry', jv.name)


def get_month_map():
	return frappe._dict({
		"January": 1,
		"February": 2,
		"March": 3,
		"April": 4,
		"May": 5,
		"June": 6,
		"July": 7,
		"August": 8,
		"September": 9,
		"October": 10,
		"November": 11,
		"December": 12
	})


@frappe.whitelist()
def get_active_fiscal_years():
	return frappe.get_all("Fiscal Year", {"disabled": 0}, ["year"])


@frappe.whitelist()
def get_from_and_to_date(fiscal_year):
	fields = ["year_start_date as from_date", "year_end_date as to_date"]
	dates = frappe.db.get_value("Fiscal Year", fiscal_year, fields, as_dict=1)
	return dates
 
def get_salary_slip_and_rate_1(payroll_entry, employee):
	filters = {'employee': employee, 'docstatus': 1, 'payroll_entry': payroll_entry}
	salary_slip_data = frappe.db.get_values('Salary Slip', filters, ['name' ,'gross_pay', 'payment_days'], as_dict=1)
	salary_slip = salary_slip_data[0].get('name')
	gross_pay = flt(salary_slip_data[0].get('gross_pay'))
	payment_days = flt(salary_slip_data[0].get('payment_days'))
	rate_per_hour = gross_pay/payment_days/8 if payment_days else 1

	return frappe._dict({'salary_slip': salary_slip, 'rate_per_hour': rate_per_hour, 'gross_pay': gross_pay, 'payment_days': payment_days})


def get_salary_slip_and_rate(employee, from_date, to_date):
	filters = {'employee': employee, 'docstatus': 1, 'start_date': ['<=', from_date], 'end_date': ['>=', to_date]}
	salary_slip_data = frappe.db.get_values('Salary Slip', filters, ['name' ,'gross_pay', 'payment_days'], as_dict=1)

	if not len(salary_slip_data):
		employee_link = frappe.get_desk_link('Employee', employee)
		frappe.msgprint(_('No Salary Slip for {0} in this Date Range {1} - {2}').format(employee_link, from_date, to_date))
		return {"employee_with_no_timesheet": employee}

	if len(salary_slip_data) > 1:
		salary_slips = '<br>'.join([frappe.get_desk_link('Salary Slip', d.name) for d in salary_slip_data])
		employee = frappe.get_desk_link('Employee', employee)
		frappe.msgprint(_('More then one Salary Slips found for {1} in this Date Range {2} - {3}:<br> {0}').format(salary_slips, employee, from_date, to_date))
		return {}


	gross_pay = salary_slip_data[0].get('gross_pay')
	payment_days = salary_slip_data[0].get('payment_days')
	salary_slip = salary_slip_data[0].get('name')
	rate_per_hour = gross_pay/payment_days/8 if payment_days else 1

	return frappe._dict({'salary_slip': salary_slip, 'rate_per_hour': rate_per_hour, 'gross_pay': gross_pay, 'payment_days': payment_days})


def get_gosi_component_amount(company, salary_slip):
	gosi_component = cost_distribution_defaults(company)['gosi_component']
	return flt(frappe.db.get_value('Salary Detail', {'parent': salary_slip, 'salary_component': gosi_component,'parentfield': 'deductions', 'parenttype': 'Salary Slip'}, 'amount')) 


@frappe.whitelist()
def get_month_start_end_date(month,year=None):
	month_map = get_month_map()
	if year:
		# year_start_date = frappe.get_cached_value("Fiscal Year", year, [""])
		today = frappe.utils.getdate()
		month_start_date = today.replace(day=1, month=int(month_map[month]), year=int(year))
		month_end_date = frappe.utils.get_last_day(month_start_date)
	else:	
		today = frappe.utils.getdate()
		month_start_date = today.replace(day=1, month=int(month_map[month]))
		month_end_date = frappe.utils.get_last_day(month_start_date)
	return frappe._dict({"from_date": month_start_date, "to_date": month_end_date})


@frappe.whitelist()
def get_time_sheet_summary(salary_data, cost_dist_doc):
	employee = salary_data.employee
	gross_pay = salary_data.gross_pay
	gosi_amount = salary_data.gosi_amount
	from_date, to_date = frappe.get_cached_value("Salary Slip", salary_data.salary_slip, ['start_date', 'end_date'])
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
		frappe.msgprint("NOT Salary Slip")
		return {"employee_with_no_timesheet": employee}

	hours = sum([d.hours for d in data])
	net_rate_per_hour = gross_pay / hours
	# gosi_amount_per_hour = gosi_amount / hours

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

	companyofpayroll = frappe.get_value("Payroll Entry", cost_dist_doc.payroll_entry, "company")
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


@frappe.whitelist()
def cost_distribution_defaults(company):
	fields = ['debit_account', 'credit_account', 'gosi_debit_account', 'default_cost_center', 'gosi_component']
	return frappe.get_cached_value("Cost Distribution Defaults", {"parent":"Cost Distribution Settings", "company": company}, fields, as_dict=1)


