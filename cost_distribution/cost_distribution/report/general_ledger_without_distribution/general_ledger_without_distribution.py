# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

# Modified to support multi-company reporting with currency conversion
# - When no specific company is selected, the report can show multiple companies
# - Each company's amounts are converted to the selected presentation currency
# - Conversion uses exchange rates from Currency Exchange doctype
# - Original amounts are preserved in debit_in_account_currency and credit_in_account_currency fields


import copy
from collections import OrderedDict

import frappe
from frappe import _, _dict
from frappe.query_builder import Criterion
from frappe.utils import cstr, getdate

from erpnext import get_company_currency, get_default_company
from erpnext.accounts.doctype.accounting_dimension.accounting_dimension import (
	get_accounting_dimensions,
	get_dimension_with_children,
)
from erpnext.accounts.report.financial_statements import get_cost_centers_with_children
from erpnext.accounts.report.utils import convert_to_presentation_currency, get_currency
from erpnext.accounts.utils import get_account_currency


def get_exchange_rate(from_currency, to_currency, transaction_date):
	"""
	Get exchange rate from one currency to another
	"""
	if from_currency == to_currency:
		return 1.0
	
	# Try to get the exchange rate from Currency Exchange doctype
	exchange_rate = frappe.db.get_value(
		"Currency Exchange",
		{
			"from_currency": from_currency,
			"to_currency": to_currency,
			"for_buying": 1
		},
		"exchange_rate",
		order_by="date desc"
	)
	
	if not exchange_rate:
		# Try reverse rate
		reverse_rate = frappe.db.get_value(
			"Currency Exchange",
			{
				"from_currency": to_currency,
				"to_currency": from_currency,
				"for_buying": 1
			},
			"exchange_rate",
			order_by="date desc"
		)
		if reverse_rate:
			exchange_rate = 1.0 / reverse_rate
	
	if not exchange_rate:
		frappe.throw(
			_("Exchange rate not found for {0} to {1}. Please add it in Currency Exchange.").format(
				from_currency, to_currency
			)
		)
	
	return exchange_rate





def execute(filters=None):
	if not filters:
		return [], []

	account_details = {}

	if filters and filters.get("print_in_account_currency") and not filters.get("account"):
		frappe.throw(_("Select an account to print in account currency"))

	for acc in frappe.db.sql("""select name, is_group from tabAccount""", as_dict=1):
		account_details.setdefault(acc.name, acc)

	if filters.get("party"):
		filters.party = frappe.parse_json(filters.get("party"))

	validate_filters(filters, account_details)

	validate_party(filters)

	filters = set_account_currency(filters)

	columns = get_columns(filters)

	res = get_result(filters, account_details)

	return columns, res


def validate_filters(filters, account_details):
	# Company is now optional
	# if not filters.get("company"):
	# 	frappe.throw(_("{0} is mandatory").format(_("Company")))

	# Make presentation_currency mandatory when company is not selected
	if not filters.get("company") and not filters.get("presentation_currency"):
		frappe.throw(_("Please select either Company or Presentation Currency"))

	if not filters.get("from_date") and not filters.get("to_date"):
		frappe.throw(
			_("{0} and {1} are mandatory").format(frappe.bold(_("From Date")), frappe.bold(_("To Date")))
		)

	if filters.get("account"):
		filters.account = frappe.parse_json(filters.get("account"))
		for account in filters.account:
			if not account_details.get(account):
				frappe.throw(_("Account {0} does not exists").format(account))

	if filters.get("account") and filters.get("group_by") == "Group by Account":
		filters.account = frappe.parse_json(filters.get("account"))
		for account in filters.account:
			if account_details[account].is_group == 0:
				frappe.throw(_("Can not filter based on Child Account, if grouped by Account"))

	if filters.get("voucher_no") and filters.get("group_by") in ["Group by Voucher"]:
		frappe.throw(_("Can not filter based on Voucher No, if grouped by Voucher"))

	if filters.from_date > filters.to_date:
		frappe.throw(_("From Date must be before To Date"))

	if filters.get("project"):
		filters.project = frappe.parse_json(filters.get("project"))

	if filters.get("cost_center"):
		filters.cost_center = frappe.parse_json(filters.get("cost_center"))


def validate_party(filters):
	party_type, party = filters.get("party_type"), filters.get("party")

	if party and party_type:
		for d in party:
			if not frappe.db.exists(party_type, d):
				frappe.throw(_("Invalid {0}: {1}").format(party_type, d))


def set_account_currency(filters):
	if filters.get("account") or (filters.get("party") and len(filters.party) == 1):
		# Get company currency - if no company selected, use presentation currency
		if filters.get("company"):
			filters["company_currency"] = frappe.get_cached_value("Company", filters.company, "default_currency")
		else:
			filters["company_currency"] = filters.get("presentation_currency")
		
		account_currency = None

		if filters.get("account"):
			if len(filters.get("account")) == 1:
				account_currency = get_account_currency(filters.account[0])
			else:
				currency = get_account_currency(filters.account[0])
				is_same_account_currency = True
				for account in filters.get("account"):
					if get_account_currency(account) != currency:
						is_same_account_currency = False
						break

				if is_same_account_currency:
					account_currency = currency

		elif filters.get("party") and filters.get("party_type"):
			# Modified to work without company filter
			gle_filters = {"party_type": filters.party_type, "party": filters.party[0]}
			if filters.get("company"):
				gle_filters["company"] = filters.company
				
			gle_currency = frappe.db.get_value("GL Entry", gle_filters, "account_currency")

			if gle_currency:
				account_currency = gle_currency
			else:
				account_currency = (
					None
					if filters.party_type in ["Employee", "Shareholder", "Member"]
					else frappe.get_cached_value(filters.party_type, filters.party[0], "default_currency")
				)

		filters["account_currency"] = account_currency or filters.company_currency
		if filters.account_currency != filters.company_currency and not filters.presentation_currency:
			filters.presentation_currency = filters.account_currency

	return filters


def get_result(filters, account_details):
	accounting_dimensions = []
	if filters.get("include_dimensions"):
		accounting_dimensions = get_accounting_dimensions()

	gl_entries = get_gl_entries(filters, accounting_dimensions)

	data = get_data_with_opening_closing(filters, account_details, accounting_dimensions, gl_entries)

	result = get_result_as_list(data, filters)

	return result


def get_gl_entries(filters, accounting_dimensions):
	currency_map = get_currency(filters)
	select_fields = """, debit, credit, debit_in_account_currency,
		credit_in_account_currency """

	if filters.get("show_remarks"):
		if remarks_length := frappe.db.get_single_value("Accounts Settings", "general_ledger_remarks_length"):
			select_fields += f",substr(remarks, 1, {remarks_length}) as 'remarks'"
		else:
			select_fields += """,remarks"""

	order_by_statement = "order by posting_date, account, creation"

	if filters.get("include_dimensions"):
		order_by_statement = "order by posting_date, creation"

	if filters.get("group_by") == "Group by Voucher":
		order_by_statement = "order by posting_date, voucher_type, voucher_no"
	if filters.get("group_by") == "Group by Account":
		order_by_statement = "order by account, posting_date, creation"

	if filters.get("include_default_book_entries") and filters.get("company"):
		filters["company_fb"] = frappe.get_cached_value(
			"Company", filters.get("company"), "default_finance_book"
		)

	dimension_fields = ""
	if accounting_dimensions:
		dimension_fields = ", ".join(accounting_dimensions) + ","

	transaction_currency_fields = ""
	if filters.get("add_values_in_transaction_currency"):
		transaction_currency_fields = (
			"debit_in_transaction_currency, credit_in_transaction_currency, transaction_currency,"
		)

	ignor = []
	if filters.get("include_payroll_distribution") == 0:
		ignor.append("COST-DIST")
	if filters.get("include_account_distribution") == 0:
		ignor.append("Account-DIST")
	if filters.get("include_project_redistribution") == 0:
		ignor.append("PROJ-REDIST-TS")
	if filters.get("include_project_over_project_distribution") == 0:
		ignor.append("POP-DIST")

	ignor_arr =["COST-DIST","Account-DIST","PROJ-REDIST-TS","POP-DIST"]

	if ignor:
		unique_values = list(set(ignor) ^ set(ignor_arr))  
		ignor_str = "|".join(unique_values)
	else:
		ignor_str = "|".join(ignor_arr)

	# Modified query to work with or without company
	company_condition = ""
	if filters.get("company"):
		company_condition = "where company=%(company)s"
	else:
		company_condition = "where 1=1"

	if filters.get("include_payroll_distribution"):
		gl_entries = frappe.db.sql(
			f"""
			select
				name as gl_entry, posting_date, account, party_type, party, company,
				voucher_type, voucher_subtype, voucher_no, {dimension_fields}
				cost_center, project, {transaction_currency_fields}
				against_voucher_type, against_voucher, account_currency,
				against, is_opening, creation {select_fields}
			from `tabGL Entry`
			{company_condition} {get_conditions(filters)}
			{order_by_statement}
		""",
			filters,
			as_dict=1,
		)
	else:
		gl_entries = frappe.db.sql(
			f"""
			select
				name as gl_entry, posting_date, account, party_type, party, company,
				voucher_type, voucher_subtype, voucher_no, {dimension_fields}
				cost_center, project, {transaction_currency_fields}
				against_voucher_type, against_voucher, account_currency,
				against, is_opening, creation {select_fields}
			from `tabGL Entry`
			{company_condition} AND remarks NOT REGEXP "Cost Distribution POP" AND ((remarks NOT REGEXP "WIP-2024" AND company = "iValueUAE") OR (remarks NOT REGEXP "WIP 2024" AND company = "iValueJOR") OR (remarks NOT REGEXP "-WIP" AND company = "iValue KSA")) {get_conditions(filters)}
			{order_by_statement}
		""",
			filters,
			as_dict=1,
		)
		

	if filters.get("presentation_currency"):
		# Get exchange rates for each company when showing multiple companies
		if not filters.get("company"):
			# Get all unique companies from GL entries
			companies = set(entry.get("company") for entry in gl_entries if entry.get("company"))
			exchange_rates = {}
			
			for company in companies:
				company_currency = frappe.get_cached_value("Company", company, "default_currency")
				
				# Get exchange rate from company currency to presentation currency
				if company_currency != filters.get("presentation_currency"):
					exchange_rate = get_exchange_rate(
						company_currency, 
						filters.get("presentation_currency"),
						filters.get("to_date")
					)
					exchange_rates[company] = exchange_rate
				else:
					exchange_rates[company] = 1.0
			
			# Convert amounts for each GL entry based on its company
			for entry in gl_entries:
				company = entry.get("company")
				if company and company in exchange_rates:
					rate = exchange_rates[company]
					
					# Store original values in account currency fields
					entry["debit_in_account_currency"] = entry.get("debit", 0)
					entry["credit_in_account_currency"] = entry.get("credit", 0)
					
					# Convert debit and credit to presentation currency
					if entry.get("debit"):
						entry["debit"] = entry["debit"] * rate
					if entry.get("credit"):
						entry["credit"] = entry["credit"] * rate
			
			return gl_entries
		else:
			# Single company - use existing conversion method
			return convert_to_presentation_currency(gl_entries, currency_map)
	else:
		return gl_entries


def get_conditions(filters):
	conditions = []

	if filters.get("account"):
		filters.account = get_accounts_with_children(filters.account)
		if filters.account:
			conditions.append("account in %(account)s")

	if filters.get("cost_center"):
		filters.cost_center = get_cost_centers_with_children(filters.cost_center)
		conditions.append("cost_center in %(cost_center)s")

	if filters.get("voucher_no"):
		conditions.append("voucher_no=%(voucher_no)s")

	if filters.get("against_voucher_no"):
		conditions.append("against_voucher=%(against_voucher_no)s")

	if filters.get("ignore_err"):
		# Modified to work without company filter
		err_filters = {"docstatus": 1, "voucher_type": ("in", ["Exchange Rate Revaluation", "Exchange Gain Or Loss"])}
		if filters.get("company"):
			err_filters["company"] = filters.get("company")
			
		err_journals = frappe.db.get_all("Journal Entry", filters=err_filters, as_list=True)
		
		if err_journals:
			filters.update({"voucher_no_not_in": [x[0] for x in err_journals]})

	if filters.get("ignore_cr_dr_notes"):
		# Modified to work without company filter
		cr_dr_filters = {
			"docstatus": 1,
			"voucher_type": ("in", ["Credit Note", "Debit Note"]),
			"is_system_generated": 1,
		}
		if filters.get("company"):
			cr_dr_filters["company"] = filters.get("company")
			
		system_generated_cr_dr_journals = frappe.db.get_all("Journal Entry", filters=cr_dr_filters, as_list=True)
		
		if system_generated_cr_dr_journals:
			vouchers_to_ignore = (filters.get("voucher_no_not_in") or []) + [
				x[0] for x in system_generated_cr_dr_journals
			]
			filters.update({"voucher_no_not_in": vouchers_to_ignore})

	if filters.get("voucher_no_not_in"):
		conditions.append("voucher_no not in %(voucher_no_not_in)s")

	if filters.get("group_by") == "Group by Party" and not filters.get("party_type"):
		conditions.append("party_type in ('Customer', 'Supplier')")

	if filters.get("party_type"):
		conditions.append("party_type=%(party_type)s")

	if filters.get("party"):
		conditions.append("party in %(party)s")

	if not (
		filters.get("account")
		or filters.get("party")
		or filters.get("group_by") in ["Group by Account", "Group by Party"]
	):
		conditions.append("(posting_date >=%(from_date)s or is_opening = 'Yes')")

	conditions.append("(posting_date <=%(to_date)s or is_opening = 'Yes')")

	if filters.get("project"):
		conditions.append("project in %(project)s")

	if filters.get("include_default_book_entries"):
		if filters.get("finance_book"):
			if filters.get("company") and filters.get("company_fb") and cstr(filters.get("finance_book")) != cstr(
				filters.get("company_fb")
			):
				frappe.throw(
					_("To use a different finance book, please uncheck 'Include Default FB Entries'")
				)
			else:
				conditions.append("(finance_book in (%(finance_book)s, '') OR finance_book IS NULL)")
		else:
			if filters.get("company_fb"):
				conditions.append("(finance_book in (%(company_fb)s, '') OR finance_book IS NULL)")
			else:
				conditions.append("(finance_book in ('') OR finance_book IS NULL)")
	else:
		if filters.get("finance_book"):
			conditions.append("(finance_book in (%(finance_book)s, '') OR finance_book IS NULL)")
		else:
			conditions.append("(finance_book in ('') OR finance_book IS NULL)")

	if not filters.get("show_cancelled_entries"):
		conditions.append("is_cancelled = 0")

	from frappe.desk.reportview import build_match_conditions

	match_conditions = build_match_conditions("GL Entry")

	if match_conditions:
		conditions.append(match_conditions)

	accounting_dimensions = get_accounting_dimensions(as_list=False)

	if accounting_dimensions:
		for dimension in accounting_dimensions:
			# Ignore 'Finance Book' set up as dimension in below logic, as it is already handled in above section
			if not dimension.disabled and dimension.document_type != "Finance Book":
				if filters.get(dimension.fieldname):
					if frappe.get_cached_value("DocType", dimension.document_type, "is_tree"):
						filters[dimension.fieldname] = get_dimension_with_children(
							dimension.document_type, filters.get(dimension.fieldname)
						)
						conditions.append(f"{dimension.fieldname} in %({dimension.fieldname})s")
					else:
						conditions.append(f"{dimension.fieldname} in %({dimension.fieldname})s")

	return "and {}".format(" and ".join(conditions)) if conditions else ""


def get_accounts_with_children(accounts):
	if not isinstance(accounts, list):
		accounts = [d.strip() for d in accounts.strip().split(",") if d]

	if not accounts:
		return

	doctype = frappe.qb.DocType("Account")
	accounts_data = (
		frappe.qb.from_(doctype)
		.select(doctype.lft, doctype.rgt)
		.where(doctype.name.isin(accounts))
		.run(as_dict=True)
	)

	conditions = []
	for account in accounts_data:
		conditions.append((doctype.lft >= account.lft) & (doctype.rgt <= account.rgt))

	return frappe.qb.from_(doctype).select(doctype.name).where(Criterion.any(conditions)).run(pluck=True)


def get_data_with_opening_closing(filters, account_details, accounting_dimensions, gl_entries):
	data = []
	totals_dict = get_totals_dict()

	gle_map = initialize_gle_map(gl_entries, filters, totals_dict)

	totals, entries = get_accountwise_gle(filters, accounting_dimensions, gl_entries, gle_map, totals_dict)

	# Opening for filtered account
	data.append(totals.opening)

	if filters.get("group_by") != "Group by Voucher (Consolidated)":
		for _acc, acc_dict in gle_map.items():
			# acc
			if acc_dict.entries:
				# opening
				data.append({"debit_in_transaction_currency": None, "credit_in_transaction_currency": None})
				if filters.get("group_by") != "Group by Voucher":
					data.append(acc_dict.totals.opening)

				data += acc_dict.entries

				# totals
				data.append(acc_dict.totals.total)

				# closing
				if filters.get("group_by") != "Group by Voucher":
					data.append(acc_dict.totals.closing)

		data.append({"debit_in_transaction_currency": None, "credit_in_transaction_currency": None})
	else:
		data += entries

	# totals
	data.append(totals.total)

	# closing
	data.append(totals.closing)

	return data


def get_totals_dict():
	def _get_debit_credit_dict(label):
		return _dict(
			account=f"'{label}'",
			debit=0.0,
			credit=0.0,
			debit_in_account_currency=0.0,
			credit_in_account_currency=0.0,
			debit_in_transaction_currency=None,
			credit_in_transaction_currency=None,
		)

	return _dict(
		opening=_get_debit_credit_dict(_("Opening")),
		total=_get_debit_credit_dict(_("Total")),
		closing=_get_debit_credit_dict(_("Closing (Opening + Total)")),
	)


def group_by_field(group_by):
	if group_by == "Group by Party":
		return "party"
	elif group_by in ["Group by Voucher (Consolidated)", "Group by Account"]:
		return "account"
	else:
		return "voucher_no"


def initialize_gle_map(gl_entries, filters, totals_dict):
	gle_map = OrderedDict()
	group_by = group_by_field(filters.get("group_by"))

	for gle in gl_entries:
		gle_map.setdefault(gle.get(group_by), _dict(totals=copy.deepcopy(totals_dict), entries=[]))
	return gle_map


def get_accountwise_gle(filters, accounting_dimensions, gl_entries, gle_map, totals):
	entries = []
	consolidated_gle = OrderedDict()
	group_by = group_by_field(filters.get("group_by"))
	group_by_voucher_consolidated = filters.get("group_by") == "Group by Voucher (Consolidated)"

	if filters.get("show_net_values_in_party_account"):
		# Modified to handle multiple companies
		account_type_map = {}
		if filters.get("company"):
			account_type_map = get_account_type_map(filters.get("company"))
		else:
			# Get all accounts from all companies
			all_accounts = frappe.db.sql("""
				SELECT name, account_type 
				FROM `tabAccount`
			""", as_dict=1)
			account_type_map = {acc.name: acc.account_type for acc in all_accounts}

	immutable_ledger = frappe.db.get_single_value("Accounts Settings", "enable_immutable_ledger")

	def update_value_in_dict(data, key, gle):
		data[key].debit += gle.debit
		data[key].credit += gle.credit

		data[key].debit_in_account_currency += gle.debit_in_account_currency
		data[key].credit_in_account_currency += gle.credit_in_account_currency

		if filters.get("add_values_in_transaction_currency") and key not in ["opening", "closing", "total"]:
			data[key].debit_in_transaction_currency += gle.debit_in_transaction_currency
			data[key].credit_in_transaction_currency += gle.credit_in_transaction_currency

		if filters.get("show_net_values_in_party_account") and account_type_map.get(data[key].account) in (
			"Receivable",
			"Payable",
		):
			net_value = data[key].debit - data[key].credit
			net_value_in_account_currency = (
				data[key].debit_in_account_currency - data[key].credit_in_account_currency
			)

			if net_value < 0:
				dr_or_cr = "credit"
				rev_dr_or_cr = "debit"
			else:
				dr_or_cr = "debit"
				rev_dr_or_cr = "credit"

			data[key][dr_or_cr] = abs(net_value)
			data[key][dr_or_cr + "_in_account_currency"] = abs(net_value_in_account_currency)
			data[key][rev_dr_or_cr] = 0
			data[key][rev_dr_or_cr + "_in_account_currency"] = 0

		if data[key].against_voucher and gle.against_voucher:
			data[key].against_voucher += ", " + gle.against_voucher

	from_date, to_date = getdate(filters.from_date), getdate(filters.to_date)
	show_opening_entries = filters.get("show_opening_entries")

	for gle in gl_entries:
		group_by_value = gle.get(group_by)
		gle.voucher_type = gle.voucher_type

		if gle.posting_date < from_date or (cstr(gle.is_opening) == "Yes" and not show_opening_entries):
			if not group_by_voucher_consolidated:
				update_value_in_dict(gle_map[group_by_value].totals, "opening", gle)
				update_value_in_dict(gle_map[group_by_value].totals, "closing", gle)

			update_value_in_dict(totals, "opening", gle)
			update_value_in_dict(totals, "closing", gle)

		elif gle.posting_date <= to_date or (cstr(gle.is_opening) == "Yes" and show_opening_entries):
			if not group_by_voucher_consolidated:
				update_value_in_dict(gle_map[group_by_value].totals, "total", gle)
				update_value_in_dict(gle_map[group_by_value].totals, "closing", gle)
				update_value_in_dict(totals, "total", gle)
				update_value_in_dict(totals, "closing", gle)

				gle_map[group_by_value].entries.append(gle)

			elif group_by_voucher_consolidated:
				keylist = [
					gle.get("posting_date"),
					gle.get("voucher_type"),
					gle.get("voucher_no"),
					gle.get("account"),
					gle.get("party_type"),
					gle.get("party"),
				]

				if immutable_ledger:
					keylist.append(gle.get("creation"))

				if filters.get("include_dimensions"):
					for dim in accounting_dimensions:
						keylist.append(gle.get(dim))
					keylist.append(gle.get("cost_center"))

				key = tuple(keylist)
				if key not in consolidated_gle:
					consolidated_gle.setdefault(key, gle)
				else:
					update_value_in_dict(consolidated_gle, key, gle)

	for value in consolidated_gle.values():
		update_value_in_dict(totals, "total", value)
		update_value_in_dict(totals, "closing", value)
		entries.append(value)

	return totals, entries


def get_account_type_map(company):
	account_type_map = frappe._dict(
		frappe.get_all("Account", fields=["name", "account_type"], filters={"company": company}, as_list=1)
	)

	return account_type_map


def get_result_as_list(data, filters):
	balance, _balance_in_account_currency = 0, 0
	inv_details = get_supplier_invoice_details()
	
	# Variables for financing cost calculation
	accumulated_cash_out = 0
	accumulated_cash_in = 0
	financing_rate = 0.14 / 12  # 14% annual rate divided by 12 months = 1.17% monthly
	accumulated_financing_cost = 0
	current_project = None
	current_month = None

	for d in data:
		if not d.get("posting_date"):
			balance, _balance_in_account_currency = 0, 0
			# Reset financing calculations for opening entries
			if filters.get("financing_costing"):
				accumulated_cash_out = 0
				accumulated_cash_in = 0
				accumulated_financing_cost = 0
				current_project = None
				current_month = None

		balance = get_balance(d, balance, "debit", "credit")
		d["balance"] = balance

		d["account_currency"] = filters.get("account_currency") or filters.get("presentation_currency")
		d["bill_no"] = inv_details.get(d.get("against_voucher"), "")
		
		# Add financing cost columns if filter is enabled
		if filters.get("financing_costing") and d.get("posting_date"):
			project = d.get("project", "")
			posting_date = d.get("posting_date")
			debit = d.get("debit", 0)
			credit = d.get("credit", 0)
			
			# Check if project changed
			if project != current_project:
				# Reset when project changes
				accumulated_cash_out = debit
				accumulated_cash_in = credit
				current_project = project
				current_month = posting_date.month if hasattr(posting_date, 'month') else None
				accumulated_financing_cost = 0
				d["trans_month"] = current_month
				d["project_code_final"] = project
			else:
				# Same project, accumulate
				accumulated_cash_out += debit
				accumulated_cash_in += credit
				
				# Check if month changed
				row_month = posting_date.month if hasattr(posting_date, 'month') else None
				if row_month != current_month:
					d["trans_month"] = row_month
					current_month = row_month
				else:
					d["trans_month"] = None
				d["project_code_final"] = None
			
			d["accumulated_cash_out"] = accumulated_cash_out
			d["accumulated_cash_in"] = accumulated_cash_in
			
			# Calculate cash difference
			cash_diff = accumulated_cash_in - accumulated_cash_out
			d["cash_diff"] = cash_diff
			
			# Calculate financing cost (only if cash_diff is negative)
			if cash_diff < 0:
				financing_cost = abs(cash_diff) * financing_rate
			else:
				financing_cost = 0
			d["financing_cost"] = financing_cost
			
			# Accumulate financing cost
			accumulated_financing_cost += financing_cost
			d["accumulated_financing_cost"] = accumulated_financing_cost
		else:
			# Set to None if financing_costing is not enabled
			d["trans_month"] = None
			d["accumulated_cash_out"] = None
			d["accumulated_cash_in"] = None
			d["cash_diff"] = None
			d["financing_cost"] = None
			d["accumulated_financing_cost"] = None
			d["project_code_final"] = None

	return data


def get_supplier_invoice_details():
	inv_details = {}
	for d in frappe.db.sql(
		""" select name, bill_no from `tabPurchase Invoice`
		where docstatus = 1 and bill_no is not null and bill_no != '' """,
		as_dict=1,
	):
		inv_details[d.name] = d.bill_no

	return inv_details


def get_balance(row, balance, debit_field, credit_field):
	balance += row.get(debit_field, 0) - row.get(credit_field, 0)

	return balance


def get_columns(filters):
	if filters.get("presentation_currency"):
		currency = filters["presentation_currency"]
	else:
		if filters.get("company"):
			currency = get_company_currency(filters["company"])
		else:
			# Default to a common currency or user's default
			company = get_default_company()
			currency = get_company_currency(company) if company else "USD"

	columns = [
		{
			"label": _("GL Entry"),
			"fieldname": "gl_entry",
			"fieldtype": "Link",
			"options": "GL Entry",
			"hidden": 1,
		},
		{"label": _("Posting Date"), "fieldname": "posting_date", "fieldtype": "Date", "width": 100},
		{
			"label": _("Account"),
			"fieldname": "account",
			"fieldtype": "Link",
			"options": "Account",
			"width": 180,
		},
	]

	# Add Company column when showing multiple companies
	if not filters.get("company"):
		columns.append({
			"label": _("Company"),
			"fieldname": "company",
			"fieldtype": "Link",
			"options": "Company",
			"width": 120,
		})

	columns += [
		{
			"label": _("Debit ({0})").format(currency),
			"fieldname": "debit",
			"fieldtype": "Float",
			"width": 130,
		},
		{
			"label": _("Credit ({0})").format(currency),
			"fieldname": "credit",
			"fieldtype": "Float",
			"width": 130,
		},
		{
			"label": _("Balance ({0})").format(currency),
			"fieldname": "balance",
			"fieldtype": "Float",
			"width": 130,
		},
	]
	
	# Add financing cost columns if filter is enabled
	if filters.get("financing_costing"):
		columns += [
			{
				"label": _("Project Code Final Entry"),
				"fieldname": "project_code_final",
				"fieldtype": "Data",
				"width": 150,
			},
			{
				"label": _("TransMonth"),
				"fieldname": "trans_month",
				"fieldtype": "Int",
				"width": 100,
			},
			{
				"label": _("Accumulated CASH OUT ({0})").format(currency),
				"fieldname": "accumulated_cash_out",
				"fieldtype": "Float",
				"width": 150,
			},
			{
				"label": _("Accumulated CASH IN ({0})").format(currency),
				"fieldname": "accumulated_cash_in",
				"fieldtype": "Float",
				"width": 150,
			},
			{
				"label": _("CASH DIFF ({0})").format(currency),
				"fieldname": "cash_diff",
				"fieldtype": "Float",
				"width": 130,
			},
			{
				"label": _("Financing Cost 1.17% ({0})").format(currency),
				"fieldname": "financing_cost",
				"fieldtype": "Float",
				"width": 150,
			},
			{
				"label": _("Accum Financing Cost ({0})").format(currency),
				"fieldname": "accumulated_financing_cost",
				"fieldtype": "Float",
				"width": 150,
			},
		]

	if filters.get("add_values_in_transaction_currency"):
		columns += [
			{
				"label": _("Debit (Transaction)"),
				"fieldname": "debit_in_transaction_currency",
				"fieldtype": "Currency",
				"width": 130,
				"options": "transaction_currency",
			},
			{
				"label": _("Credit (Transaction)"),
				"fieldname": "credit_in_transaction_currency",
				"fieldtype": "Currency",
				"width": 130,
				"options": "transaction_currency",
			},
			{
				"label": "Transaction Currency",
				"fieldname": "transaction_currency",
				"fieldtype": "Link",
				"options": "Currency",
				"width": 70,
			},
		]

	columns += [
		{"label": _("Voucher Type"), "fieldname": "voucher_type", "width": 120},
		{
			"label": _("Voucher Subtype"),
			"fieldname": "voucher_subtype",
			"fieldtype": "Data",
			"width": 180,
		},
		{
			"label": _("Voucher No"),
			"fieldname": "voucher_no",
			"fieldtype": "Dynamic Link",
			"options": "voucher_type",
			"width": 180,
		},
		{"label": _("Against Account"), "fieldname": "against", "width": 120},
		{"label": _("Party Type"), "fieldname": "party_type", "width": 100},
		{"label": _("Party"), "fieldname": "party", "width": 100},
		{"label": _("Project"), "options": "Project", "fieldname": "project", "width": 100},
	]

	if filters.get("include_dimensions"):
		for dim in get_accounting_dimensions(as_list=False):
			columns.append(
				{"label": _(dim.label), "options": dim.label, "fieldname": dim.fieldname, "width": 100}
			)
		columns.append(
			{"label": _("Cost Center"), "options": "Cost Center", "fieldname": "cost_center", "width": 100}
		)

	columns.extend(
		[
			{"label": _("Against Voucher Type"), "fieldname": "against_voucher_type", "width": 100},
			{
				"label": _("Against Voucher"),
				"fieldname": "against_voucher",
				"fieldtype": "Dynamic Link",
				"options": "against_voucher_type",
				"width": 100,
			},
			{"label": _("Supplier Invoice No"), "fieldname": "bill_no", "fieldtype": "Data", "width": 100},
		]
	)

	if filters.get("show_remarks"):
		columns.extend([{"label": _("Remarks"), "fieldname": "remarks", "width": 400}])

	return columns
