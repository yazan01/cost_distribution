// Copyright (c) 2024, Furqan Asghar and contributors
// For license information, please see license.txt

frappe.ui.form.on("Manual Distribution", {
	refresh(frm) {
        if (!frm.is_new() && !frm.doc.journal_entry && frm.doc.docstatus<2) {
			frm.add_custom_button(__('Create Journal Entry'), function () {
				frappe.call({
					doc: frm.doc,
					method: 'create_journal_entry',
					callback: function() {
						frm.refresh();
					}
				})
			});
		}
        if (frm.doc.journal_entry) {
			$('div[data-fieldname="jv_frame"]').html(frappe.render_template(`
			
				<iframe src="`+ frappe.urllib.get_full_url("app/journal-entry/" + frm.doc.journal_entry) + `" title="description" style="
					width: 100%;
					height: 100%;
				"></iframe>
			`)).show()
			$('div[data-fieldname="jv_frame"]').css("height", "500px")
		} else {
			$('div[data-fieldname="jv_frame"]').html("")
		}
	},

    onload: function(frm) {
		frm.trigger("set_queries");
		frm.trigger("set_defaults");
	},

	company: function(frm) {
		frm.trigger("set_queries");
		frm.trigger("set_defaults");
	},
    
    set_defaults: function(frm) {
		if (frm.doc.docstatus == 0 || frm.is_new()) {
			frappe.call({
				method: "cost_distribution.cost_distribution.doctype.manual_distribution.manual_distribution.manual_distribution_defaults",
				args: {
					'company': frm.doc.company
				},
				callback: function(r) {
					if(r.message) {
						console.log(r.message);
						frm.set_value(r.message);
					} else {
						frm.set_value('debit_account', '');
						frm.set_value('credit_account', '');
						// frm.set_value('gosi_debit_account', '');
						frm.set_value('default_cost_center', '');
					}
					frm.refresh_fields();
				}
			})
		}
	},


    set_queries: function (frm) {
		frm.set_query('debit_account', function() {
			return {
				filters: {
					company: frm.doc.company,
					is_group: 0
				},
			};
		});

		frm.set_query('credit_account', function() {
			return {
				filters: {
					company: frm.doc.company,
					is_group: 0
				},
			};
		});

		// frm.set_query('employee', function() {
		// 	return {
		// 		filters: {
		// 			company: frm.doc.company,
		// 		},
		// 	};
		// });

	},
});
frappe.ui.form.on('Project Summary', {
	project: function (frm, cdt, cdn) {
		debugger;
		if (['Project', 'Manual'].includes(frm.doc.distribution_type)) {
			var row = frappe.get_doc(cdt, cdn);
			
			frappe.db.get_value("Project", row.project, ["project_cost", "cost_center"], (r) => {
				if (r && !r.exc) {
					frappe.model.set_value(cdt, cdn, 'total_cost_of_project', flt(r.project_cost));
					frappe.model.set_value(cdt, cdn, 'cost_center', r.cost_center);
				}
			});
		}
	},
});