// Copyright (c) 2024, Furqan Asghar and contributors
// For license information, please see license.txt

frappe.ui.form.on("CTC Distribution", {
	
    onload: function(frm) {
		frm.trigger("set_queries");
		frm.trigger("set_defaults");
	},

	company: function(frm) {
		frm.trigger("set_queries");		
	}

});


frappe.ui.form.on('CTC Distribution', {
	to_date: function (frm) {
		frm.set_value('posting_date', frm.doc.to_date);
	}
});



frappe.ui.form.on('Project Summary CTC', {
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
