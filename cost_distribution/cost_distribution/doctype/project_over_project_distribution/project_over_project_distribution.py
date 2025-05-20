# Copyright (c) 2025, Yazan Hamdan and Reem Alomari
# For license information, please see license.txt

from frappe.model.document import Document
import frappe
from frappe import _
from frappe.utils import flt, cstr


class ProjectOverProjectDistribution(Document):
    def validate(self):
        """Validates and processes salary slips and costing summary."""
        self.validate_fields()
        self.set_project_source_and_total()
        self.create_transaction_list()
        self.set_cost_center()

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
        """Validates required fields for Project Over Project Distribution."""
        required_fields = {
            "Company": self.company,
            "Child Cost Center": self.sub_cost_centers,
            "Start Date": self.from_date,
            "End Date": self.to_date,
        }
        missing_fields = [field for field, value in required_fields.items() if not value]
        if missing_fields:
            frappe.throw(_("Please set the following fields: {0}").format(", ".join(missing_fields)))

        
    @frappe.whitelist()
    def set_project_source_and_total(self):
        """Fetches and sets salary slip data based on Project Over Project Distribution type."""
        if self.distribution_type == 'Project Over Project Distribution':
            if not self.projects_source:
                self.projects_source = []

                for row in self.sub_cost_centers:              
                    cost_center = row.sub_cost_center
                    last_dash_index = cost_center.rfind('-')
                    cost_center = cost_center[:last_dash_index].strip()

                    cost_center_like = cost_center+"%"

                    result = frappe.db.sql(
                        """
                        SELECT 
                            p.name AS project, 
                            p.project_name AS project_name,
                            gle.debit-gle.credit AS total
                        FROM
                            (SELECT 
                                name, 
                                project_name
                            FROM
                                `tabProject` AS p 
                            WHERE 
                                cost_center LIKE %s
                            ) AS p
                        LEFT JOIN
                            (SELECT 
                                project,
                                SUM(debit) AS debit,
                                SUM(credit) AS credit
                            FROM 
                                `tabGL Entry`
                            WHERE 
                                docstatus = 1
                                AND is_cancelled = 0
                                AND posting_date BETWEEN %s AND %s
                                AND company = %s  
                                AND cost_center LIKE %s
                                AND account LIKE %s OR account LIKE %s   
                            GROUP BY 
                                project                 
                        ) AS gle
                        ON 
                            p.name = gle.project;
                    """,
                        (cost_center_like,self.from_date, self.to_date, self.company, cost_center_like, '5%', '4%'), as_dict=True,
                    )
                    if not result:
                        frappe.throw(_("No Employee in This Account"))

                    if self.company == "iValueJOR":
                        cost_center += " - iJOR"
                    elif self.company == "iValueUAE":
                        cost_center += " - iUAE"
                    elif self.company == "iValue KSA":
                        cost_center += " - iKSA"
                    else:
                        cost_center += " - iV"

                    
                    for row1 in result:
                        if flt(row1.get('total')) != 0 and (flt(row1.get('total')) >= 0.02 or flt(row1.get('total')) <= -0.02):
                            self.append('projects_source', {
                                'project': row1.get('project'),
                                'project_name': row1.get('project_name'),
                                'total': flt(row1.get('total')),
                                'cost_center': cost_center,
                            })
      
    @frappe.whitelist()
    def create_transaction_list(self):
        """Creates a costing summary for the document."""
        if self.distribution_type not in ['Employee', 'Project Over Project Distribution']:
            return
        if not self.transaction_entry_child:
            self.transaction_entry_child = []
            total_cost_of_project = 0
            
            for project in self.projects_source:

                if self.projects_source_check == 1:

                    result = frappe.db.sql(
                        """
                        SELECT 
                            account,
                            project,
                            cost_center,
                            SUM(debit)-SUM(credit) AS total
                        FROM 
                            `tabGL Entry`
                        WHERE 
                            docstatus = 1
                            AND is_cancelled = 0
                            AND posting_date BETWEEN %s AND %s
                            AND company = %s  
                            AND cost_center = %s   
                            AND project = %s
                        GROUP BY 
                            account              
                    """,
                        (self.from_date, self.to_date, self.company, project.cost_center, project.project), as_dict=True,
                    )

                    for row2 in result:
                        if round(flt(row2.get('total')), 2) != 0 and (row2.get('account').startswith('5') or row2.get('account').startswith('4')):
                            r_total = round(flt(row2.get('total')), 2)                    
                            self.append('transaction_entry_child', {
                                'account': row2.get('account'),
                                'project': row2.get('project'),
                                'cost_center': row2.get('cost_center'),
                                'total': r_total
                            })                
                            total_cost_of_project += r_total

            self.amount = total_cost_of_project
        else:
            total_cost_of_project = 0
            for t in self.transaction_entry_child:
                total_cost_of_project += flt(t.total)
            self.amount = total_cost_of_project

    @frappe.whitelist()
    def set_cost_center(self):
        
        if self.target_projects:
            for row in self.target_projects:
                
                cost_center = frappe.get_cached_value('Project', row.get('project'), 'cost_center')
                last_dash_index = cost_center.rfind('-')
                if last_dash_index != -1:
                    cost_center = cost_center[:last_dash_index].strip()
                if self.company == "iValueJOR":
                    cost_center += " - iJOR"
                elif self.company == "iValueUAE":
                    cost_center += " - iUAE"
                elif self.company == "iValue KSA":
                    cost_center += " - iKSA"
                else:
                    cost_center += " - iV"

                row.cost_center = cost_center

    @frappe.whitelist()
    def create_journal_entry(self):
        self.validate()
        precision = frappe.get_precision("Journal Entry Account", "debit_in_account_currency")
        jv = frappe.new_doc("Journal Entry")
        jv.company = self.company
        jv.posting_date = self.posting_date
        jv.user_remark = 'JV Created VIA {0}'.format(frappe.get_desk_link('Cost Distribution', self.name))


        if not self.target_projects:
            frappe.throw('Target Projects Table is Empty')

        #credit
        for d in self.transaction_entry_child:
            if d.total < 0:
                jv.append('accounts', {
                    'project': d.project,
                    'cost_center': d.cost_center,
                    'account': d.account,
                    'debit_in_account_currency': (flt(d.total)* -1)
                })
            else:
                 jv.append('accounts', {
                    'project': d.project,
                    'cost_center': d.cost_center,
                    'account': d.account,
                    'credit_in_account_currency': flt(d.total)
                })

        #debit
        for d in self.transaction_entry_child:
            for p in self.target_projects:
                amount = flt((d.total * p.perc_distribution)/100)
                #amount = round(amount_1, 2)
                if d.total < 0:
                    jv.append('accounts', {
                        'project': p.project,
                        'cost_center': p.cost_center,
                        'account': d.account,
                        'credit_in_account_currency': (flt(amount)* -1)
                    })
                else:
                    jv.append('accounts', {
                        'project': p.project,
                        'cost_center': p.cost_center,
                        'account': d.account,
                        'debit_in_account_currency': flt(amount)
                    })

        if self.company == "iValueJOR":
            cost_center = "3001 - Overhead Cost - iJOR"
            account = "5212 - Round Off - iJOR"
        elif self.company == "iValueUAE":
            cost_center = "3001 - Overhead Cost - iUAE"
            account = "5212 - Round Off - iUAE"
        elif self.company == "iValue KSA":
            cost_center = "3001 - Overhead Cost - iKSA"
            account = "5212 - Round Off - iKSA"
        else:
            cost_center = "3001 - Overhead Cost - iV"
            account = "5212 - Round Off - iV"

        tt = self.division_difference
        if tt > 0:
            jv.append('accounts', {
                'project': "PROJ-0027",
                'cost_center': cost_center,
                'account': account,
                'credit_in_account_currency': flt(tt)
            })
        elif tt < 0:
            jv.append('accounts', {
                'project': "PROJ-0027",
                'cost_center': cost_center,
                'account': account,
                'debit_in_account_currency': flt(tt*-1)
            })

        jv.save()
        self.db_set('journal_entry', jv.name)


