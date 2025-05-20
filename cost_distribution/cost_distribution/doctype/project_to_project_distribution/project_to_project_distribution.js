// Copyright (c) 2024, Furqan Asghar and contributors
// For license information, please see license.txt


function print_filtered_project_values(frm) {
    let cost_center_values = [];
    for (let i = 0; i < frm.doc.sub_cost_center.length; i++) {
        let row = frm.doc.sub_cost_center[i];
        cost_center_values.push(row.sub_cost_center);
    }
    if (frm.doc.purchase_check == 0) {
        frappe.db.get_list('Project', {
            filters: {
                cost_center: ['in', cost_center_values]
            },
            fields: ['name', 'cost_center', 'project_cost']
        }).then((projects) => {
            for (let val of projects) {
                let source_row = frm.add_child('source_project');
                source_row.project = val.name;
                source_row.cost_center = val.cost_center;
                // source_row.total_cost_of_project = val.project_cost;
            }
            frm.refresh_field('source_project');
        });
    } else if (frm.doc.purchase_check == 1) {
        console.log("purchase working-------------------")
        frappe.db.get_list('Cost Center', {
            filters: {
                name: ['in', cost_center_values]
            },
            fields: ['name']
        }).then((invoices) => {
            console.log(invoices,"project----------------")
            for (let val of invoices) {
                console.log("purchase----",val)
                let source_row = frm.add_child('source_project');
                source_row.cost_center = val.name;
            }
            frm.refresh_field('source_project');
        });
    }
}

frappe.ui.form.on("Project To Project Distribution", {
    // validate: function(frm) {
    //     frm.set_value('sub_cost_center', selected_values.join(', '));
    //     frm.save();
    //     var display_total_debit = 0
	// 	var display_total_credit = 0
    //     if (frm.doc.transaction_entry_child) {
    //         $.each(frm.doc.transaction_entry_child, function (index, row) {
    //             if (!row.project) {
    //                 console.log(row.debit_amount, "debit_amount------");
    //                 display_total_debit += flt(row.debit_amount, 2) || 0.00;
    //                 display_total_credit += flt(row.credit_amount, 2) || 0.00;
    //                 console.log(flt(display_total_credit, 2), 'djfhskdfkshd');
    //             }
	// 		})
        // },
	// 	if (!frm.is_new() && frm.doc.transaction_entry_child && frm.doc.transaction_entry_child.length > 1) {
	// 		$('.total-bl-wrapper').remove();
	// 		var totalbleHtml = `<div class="grid-row" data-name="sqgo3lemmh" data-idx="1">
    //             <div class="data-row row" style ="border:1px solid;background-color:lightgrey">
    //                 <div class="row-check sortable-handle col" rowspan="2" style="margin-left: 56px; text-align: center;"">
    //                 <span><b>Total</b></span>
    //                 </div>
    //                 <div class="col grid-static-col col-xs-1 " data-fieldname="posting_date" data-fieldtype="Date">
    //                 <div class="field-area" style="display: none;"></div>
    //                 <div class="static-area ellipsis"></div>
    //                 </div>
    //                 <div class="col grid-static-col col-xs-1 " data-fieldname="account" data-fieldtype="Link">
    //                 <div class="field-area" style="display: none;"></div>
    //                 <div class="static-area ellipsis">
    //                 </div>
    //                 </div>
    //                 <div class="col grid-static-col col-xs-1  text-right" data-fieldname="debit_amount" data-fieldtype="Currency">
    //                 <div class="field-area" style="display: none;"></div>
    //                 <div class="static-area ellipsis">
    //                     <div style="text-align: right"><strong>${display_total_debit.toLocaleString('en-IN')}ر.س </strong></div>
    //                 </div>
    //                 </div>
    //                 <div class="col grid-static-col col-xs-1  text-right" data-fieldname="credit_amount" data-fieldtype="Currency">
    //                 <div class="field-area" style="display: none;"></div>
    //                 <div class="static-area ellipsis">
    //                     <div style="text-align: right"><strong>${display_total_credit.toLocaleString('en-IN')}ر.س </strong></div>
    //                 </div>
    //                 </div>
    //                 <div class="col grid-static-col col-xs-1 " data-fieldname="voucher_no" data-fieldtype="Dynamic Link">
    //                 <div class="field-area" style="display: none;"></div>
    //                 <div class="static-area ellipsis">
    //                 </div>
    //                 </div>
    //                 <div class="col grid-static-col col-xs-1 " data-fieldname="voucher_type" data-fieldtype="Link">
    //                 <div class="field-area" style="display: none;"></div>
    //                 <div class="static-area ellipsis">
    //                 </div>
    //                 </div>
    //                 <div class="col grid-static-col col-xs-1 " data-fieldname="party_type" data-fieldtype="Link">
    //                 <div class="field-area" style="display: none;"></div>
    //                 <div class="static-area ellipsis"></div>
    //                 </div>
    //                 <div class="col grid-static-col col-xs-1 " data-fieldname="party" data-fieldtype="Dynamic Link">
    //                 <div class="field-area" style="display: none;"></div>
    //                 <div class="static-area ellipsis"></div>
    //                 </div>
    //                 <div class="col grid-static-col col-xs-1 " data-fieldname="project" data-fieldtype="Link">
    //                 <div class="field-area" style="display: none;"></div>
    //                 <div class="static-area ellipsis">
    //                 </div>
    //                 </div>
    //                 <div class="col grid-static-col col-xs-1 " data-fieldname="cost_center" data-fieldtype="Link">
    //                 <div class="field-area" style="display: none;"></div>
    //                 <div class="static-area ellipsis">
    //                 </div>
    //                 </div>
    //                 <div class="col">
    //                 <div class="btn-open-row" data-toggle="tooltip" data-placement="right" title="" data-original-title="Edit">
                        
    //                 </div>
    //                 </div>
    //             </div>
    //             </div>`;
    //             if ($('.total-bl-wrapper').length === 0) {
    //                 $("[data-fieldname=transaction_entry_child] .grid-body .rows").after(totalbleHtml);
    //             }
	// 	}
    // },
    project_update: function(frm) {
        print_filtered_project_values(frm);
    },
    get_transaction: function(frm) {
        frappe.call({
            doc: frm.doc,
            method: 'create_transaction_list',
            callback: function (data) {
                console.log(data, 'Transaction List Response');
                frm.reload_doc();
            },
        });
    },
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
        
        frm.set_query("parent_cost_center", function() {
            return {
                filters: {
                    'is_group': 1
                }
            };
        });
        frm.set_query("sub_cost_center", function() {
            return {
                filters: {
                    'parent_cost_center': frm.doc.parent_cost_center
                }
            };
        });
	},
    

    onload: function(frm) {
		frm.trigger("set_queries");
		frm.trigger("set_defaults");
	},

	company: function(frm) {
		frm.trigger("set_queries");
		frm.trigger("set_defaults");
	},

    // set_defaults: function(frm) {
	// 	if (frm.doc.docstatus == 0 || frm.is_new()) {
	// 		frappe.call({
	// 			method: "cost_distribution.cost_distribution.doctype.project_to_project_distribution.project_to_project_distribution.project_distribution_defaults",
	// 			args: {
	// 				'company': frm.doc.company
	// 			},
	// 			callback: function(r) {
	// 				if(r.message) {
	// 					console.log(r.message);
	// 					frm.set_value(r.message);
	// 				} else {
	// 					frm.set_value('debit_account', '');
	// 					frm.set_value('credit_account', '');
	// 					// frm.set_value('gosi_debit_account', '');
	// 					frm.set_value('default_cost_center', '');
	// 				}
	// 				frm.refresh_fields();
	// 			}
	// 		})
	// 	}
	// },

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