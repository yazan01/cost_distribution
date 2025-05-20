// Copyright (c) 2024, Yazan Hamdan and Reem Alomari
// For license information, please see license.txt

frappe.ui.form.on("Project Over Project Distribution", {
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
	},

   

    

});
frappe.ui.form.on('Project Over Project Distribution', {
	to_date: function (frm) {
		frm.set_value('posting_date', frm.doc.to_date);
	}
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

frappe.ui.form.on('Project Over Project Distribution', {
    refresh: function(frm) {
        setupCostCenterFilter(frm);
    },
    company: function(frm) {
        setupCostCenterFilter(frm);
    }
});

function setupCostCenterFilter(frm) {
    frm.set_query('sub_cost_centers', function(doc) {
        return {
            filters: {
                'company': doc.company,
                'is_group': 0  
            },
            page_length: 9999
        };
    });
}


frappe.ui.form.on('Project Cost Center Child', {
    form_render: function(frm, cdt, cdn) {
        
        var child = locals[cdt][cdn];
        var parent = frm.doc;
        
        if (parent.company) {
            frm.fields_dict.sub_cost_centers.grid.get_field('cost_center').get_query = function() {
                return {
                    filters: {
                        'company': parent.company,
                        'is_group': 0
                    }
                };
            };
        }
    }
});