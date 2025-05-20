import frappe
from frappe import _

def submit_source_cost_distribution_if_exist(doc, method=None):
	if frappe.db.exists('Cost Distribution', {'journal_entry': doc.name}):
		cost_distribution = frappe.get_doc('Cost Distribution', {'journal_entry': doc.name})
		if cost_distribution.docstatus == 0:
			cost_distribution.submit()
			frappe.msgprint(_('{0} Submitted').format(frappe.get_desk_link('Cost Distribution', cost_distribution.name)))

		if cost_distribution.docstatus == 2:
			frappe.throw(_('Linked {0} is cancelled, please unlink Journal Entry from this doc first').format(frappe.get_desk_link('Cost Distribution', cost_distribution.name)))