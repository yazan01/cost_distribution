# Copyright (c) 2024, Furqan Asghar and contributors
# For license information, please see license.txt

from frappe.model.document import Document
import frappe
from frappe import _
from frappe.utils import flt, cstr, cint

class ManualDistribution(Document):
	def validate(self):
		# self.set_salary_slip_and_rate1()
		# self.set_salary_slip_and_rate()
		# self.create_costing_summary()
		# self.remove_employees_with_no_hours()
		self.validate_costing_summary()
		# self.validate_total_hours()
		# self.check_duplicate()

	def on_submit(self):
		if self.journal_entry:
			jv = frappe.get_doc('Journal Entry', self.journal_entry)
			jv.submit()
		else:
			frappe.throw(_('Not Journal Entry linked.'))
	
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

	@frappe.whitelist()
	def create_journal_entry(self):
		precision = frappe.get_precision("Journal Entry Account", "debit_in_account_currency")
		jv = frappe.new_doc("Journal Entry")
		jv.company = self.company
		jv.posting_date = self.posting_date
		jv.user_remark = 'JV Created VIA {0}'.format(frappe.get_desk_link('Cost Distribution', self.name))

		jv.append('accounts', {
			'account': self.credit_account,
			'credit_in_account_currency': flt(self.amount, precision)
		})

		if self.distribution_type == 'Manual':
			for d in self.costing_summary:
				d.debit = flt(d.total_cost_of_project, precision)

		##### if there's rounding difference in debit then appending in last row
		diff = self.amount - sum([d.debit for d in self.costing_summary])
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
	
	@frappe.whitelist()
	def get_time_sheet_summary(salary_data, cost_dist_doc):
		print("55555555555555555555555555555555555555555555555555555S")
		employee = salary_data.employee
		gross_pay = salary_data.gross_pay
		gosi_amount = salary_data.gosi_amount
		from_date, to_date = frappe.get_cached_value("Salary Slip", salary_data.salary_slip, ['start_date', 'end_date'])
		default_cost_center = cost_dist_doc.default_cost_center

		data = frappe.db.sql(
			"""SELECT ts.name as timesheet, tsd.project, tsd.from_time, tsd.to_time, tsd.hours, tsd.name  as timesheet_child
			FROM `tabTimesheet` ts , `tabTimesheet Detail` tsd 
			WHERE ts.docstatus=1 AND ts.name = tsd.parent AND ts.employee=%s AND ts.docstatus=1 AND 
			tsd.from_time>=%s AND tsd.to_time<=%s""",
			(employee, from_date, to_date), as_dict=True,
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
			print(data_dict[k]['total_cost_of_project'] ,"/", total_cost_of_all_projects,"100")
			project_list.append(frappe._dict({
				'project': k, 
				'cost_per_hour': net_rate_per_hour,
				'total_hours': data_dict[k]['total_hours'], 
				'gosi_amount': data_dict[k]['gosi_amount'],
				'timesheets_data': cstr(data_dict[k]['timesheets_data']),
				'total_cost_of_project': data_dict[k]['total_cost_of_project'],
				'perc_distribution': (data_dict[k]['total_cost_of_project'] / (total_cost_of_all_projects or 1)) * 100
			}))

		for d in project_list:
			cost_center = frappe.db.get_value('Projectwise Cost Center', {"parent": employee, "project": d.get('project')}, 'cost_center')
			print(cost_center,'cost_center',employee,d.get('project'))
			if cost_center:
				d['cost_center'] = cost_center
			else:
				frappe.throw(_("Please set Payroll Cost Center in {0} for Project {1}").format(frappe.get_desk_link("Employee", employee), frappe.get_desk_link("Project", d.get('project'))))

			# if d.get('project'):
			# 	d['cost_center'] = frappe.get_cached_value('Project', d.get('project'), 'cost_center')
			# else:
			# 	d['cost_center'] = default_cost_center

		
		##### if there's rounding difference then appending in last project
		if project_list:
			diff = 100 - sum([d.perc_distribution for d in project_list])
			if diff:
				project_list[-1]['perc_distribution'] += diff

		return {"project_list": project_list}

@frappe.whitelist()
def manual_distribution_defaults(company):
	print("workingg --------------------------------")
	fields = ['debit_account', 'credit_account', 'default_cost_center']
	return frappe.get_cached_value("Manual Distribution Defaults", {"parent":"Manual Distribution Settings", "company": company}, fields, as_dict=1)



	# pass