# Copyright (c) 2024, Furqan Asghar and contributors
# For license information, please see license.txt
from frappe.model.document import Document
import frappe
from frappe import _
from frappe.utils import flt, cstr, cint


class ProjectToProjectDistribution(Document):
	def validate(self):
		# self.set_salary_slip_and_rate1()
		# self.set_salary_slip_and_rate()
		self.create_target_projects()
		# self.remove_employees_with_no_hours()
		self.validate_target_projects()
		# self.validate_total_hours()
		# self.check_duplicate()
		

	def on_submit(self):
		if self.journal_entry:
			jv = frappe.get_doc('Journal Entry', self.journal_entry)
			jv.submit()
		else:
			frappe.throw(_('Not Journal Entry linked.'))
	
	def validate_target_projects(self):
		# if self.distribution_type != 'Manual':
		# 	perc_distribution = 0
		# 	for d in self.target_projects:
		# 		perc_distribution += d.perc_distribution

		# 	if perc_distribution != 100:
		# 		frappe.throw(_('Cost Distribution Percentage should be 100%'))

		if self.distribution_type == 'Manual':
			total_cost_of_projects = sum([d.total_cost_of_project for d in self.target_projects])
			if self.amount != total_cost_of_projects:
				frappe.throw(_('In manual distribution total project cost {0} should be equal to {1} debit amount').format(total_cost_of_projects, self.amount))

	@frappe.whitelist()
	def create_target_projects(self):
		print(self.distribution_type,'----------------')
		if self.distribution_type == 'Project':
			print("hjSDfsdhgfjsgdfjgsdhfsh")
			self.target_projects = [d for d in self.target_projects if d.project]

			for d in self.target_projects:
				if not d.total_cost_of_project:
					frappe.throw(_('Project Cost missing in Row {}').format(d.idx))
			total_cost_of_all_projects = sum([d.total_cost_of_project for d in self.target_projects])
			print(total_cost_of_all_projects,'total_cost_of_all_projects-----------')
			for d in self.target_projects:
				d.perc_distribution = (d.total_cost_of_project / total_cost_of_all_projects) * 100
				print(d.perc_distribution,'d.perc_distribution')

	@frappe.whitelist()
	def create_transaction_list(self):
		row_list = [
			{"project": i.project, "cost_center": i.cost_center}
			for i in self.source_project if i.select_row
		]

		self.transaction_entry_child = []
		total_debit = 0

		for row in row_list:
			gl_entries = frappe.db.get_list(
				"GL Entry",
				filters={
					"project": row["project"],
					"cost_center": row["cost_center"],
					"voucher_type": ["in", ["Journal Entry", "Purchase Invoice"]],
					"docstatus": 1,
					"is_cancelled": 0
				},
				fields=["*"]
			)

			for gl_entry in gl_entries:
				print(gl_entry['docstatus'],gl_entry['is_cancelled'])
				if gl_entry["debit"] > 0:
					self.debit_account = gl_entry['account']
					self.credit_account = gl_entry['account']
					self.default_cost_center = gl_entry['cost_center']
					child = self.append("transaction_entry_child", {})
					child.project = gl_entry["project"]
					child.account = gl_entry["account"]
					child.cost_center = gl_entry["cost_center"]
					child.party = gl_entry.get("party")
					child.party_type = gl_entry.get("party_type")
					child.posting_date = gl_entry["posting_date"]
					child.voucher_no = gl_entry["voucher_no"]
					child.voucher_type = gl_entry["voucher_type"]
					child.debit_amount = gl_entry["debit"]
					child.credit_amount = gl_entry["credit"]

					total_debit += gl_entry["debit"]

		self.amount = total_debit
		self.save()

		frappe.msgprint("Transaction list created successfully!")

	
	@frappe.whitelist()
	def create_journal_entry(self):
		self.validate()
		precision = frappe.get_precision("Journal Entry Account", "debit_in_account_currency")
		jv = frappe.new_doc("Journal Entry")
		jv.company = self.company
		jv.posting_date = self.posting_date
		jv.user_remark = 'JV Created VIA {0}'.format(frappe.get_desk_link('Project To Project Distribution', self.name))

		# jv.append('accounts', {
		# 	'account': self.credit_account,
		# 	'cost_center': self.default_cost_center,#neww
		# 	'credit_in_account_currency': flt(self.amount, precision)
		# })

		# for d in self.target_projects:
		# 	d.credit = flt(d.total_cost_of_project, precision) if self.distribution_type == 'Manual' else flt((self.amount * d.perc_distribution)/100, precision)

		if not self.target_projects:
			frappe.throw('Costing Summary Table is Empty')

		
		# if self.distribution_type == 'Project':
		# 	for d in self.target_projects:
		# 		# print(d,'dddddddddddddddddddddddddd')
		# 		d.debit = flt((self.amount * d.perc_distribution)/100, precision)
				# print(d.debit,'dhsdjfhsfhsjdh')

		##### if there's rounding difference in debit then appending in last row
		# diff = self.amount - sum([d.debit for d in self.target_projects])
		# if diff:
		# 	for d in self.target_projects:
		# 		if d.idx == len(self.target_projects):
		# 			d.debit += diff

		# for d in self.target_projects:
		# 	jv.append('accounts', {
		# 		'party': d.employee if self.distribution_type in ['Employee', 'All Employee'] else None,
		# 		'party_type': 'Employee' if self.distribution_type in ['Employee', 'All Employee'] else None,
		# 		'project': d.project,
		# 		'cost_center': d.cost_center,
		# 		'account': self.debit_account,
		# 		'debit_in_account_currency': d.debit
		# 	})
			# print(jv,'jvvvvvvvvvvv')
		
		list_val = {}
		for transaction in self.transaction_entry_child:
			if transaction.project:
				if transaction.project not in list_val:
					list_val[transaction.project] = {
						'project': transaction.project,
						'account': transaction.account,
						'cost_center': transaction.cost_center,
						'party':transaction.party,
						'party_type':transaction.party_type,
						'credit_tot': 0,
						'debit_tot': 0,
					}
				list_val[transaction.project]['credit_tot'] = transaction.debit_amount or 0

				final_list = list(list_val.values())
				# print(final_list, 'Final merged list of dictionaries')

				for val in final_list:
					# print(val, '---------------------------------------------')
					jv.append('accounts', {
						'account': val['account'],
						'project': val['project'],
						'party': val['party'],
						'party_type':val['party_type'],
						'cost_center': val['cost_center'],
						'credit_in_account_currency': val['credit_tot'],
						# 'debit': val['debit_tot'],
						# 'credit': val['credit_tot'],
					})
		debit_list = []
		for d_val in self.transaction_entry_child:
			debit_list.append(d_val.debit_amount)
			for d in self.target_projects:
				# print(d_val.debit_amount,'d_val.debit_amount')
				debit_amount = flt((d_val.debit_amount * d.perc_distribution)/100, precision)
				print(debit_amount ,'*',d.perc_distribution,'/100')
				# print(d_val.debit_amount,'dhsdjfhsfhsjdh-----',t_val.perc_distribution)
				jv.append('accounts', {
					'party': d_val.party, #if self.distribution_type in ['Employee', 'All Employee'] else None,
					'party_type':  d_val.party_type, # if self.distribution_type in ['Employee', 'All Employee'] else None,
					'project': d_val.project,
					'cost_center': d_val.cost_center,
					'account': d_val.account,
					'debit_in_account_currency': debit_amount,
					# 'debit': d_val.debit_amount,
					# 'credit': d_val.credit_amount
				})
		# debit = 0
		# for d in self.target_projects:
		# 	# print(debit_list,'d_val.debit_amount----tttttttt')
		# 	for amt in debit_list:
		# 		debit = flt((amt * d.perc_distribution)/100, precision)
		# 		print(debit,'fbdjfhkfdhgjkhdf')
		# 		jv.append('accounts', {
		# 			'debit_in_account_currency': debit
		# 		})
		# 		print(jv, 'jvvvv--------------------vvvvvvv')
		# oooooooooooooooooooooooooooooooo
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

# @frappe.whitelist()
# def project_distribution_defaults(company):
# 	fields = ['debit_account', 'credit_account','default_cost_center']
# 	return frappe.get_cached_value("Project to Project Distribution Defaults", {"parent":"Project To Project Distribution Settings", "company": company}, fields, as_dict=1)


	# pass
