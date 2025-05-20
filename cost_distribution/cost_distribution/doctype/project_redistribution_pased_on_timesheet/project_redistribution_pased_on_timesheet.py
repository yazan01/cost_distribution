# Copyright (c) 2024, Furqan Asghar and contributors
# For license information, please see license.txt

from frappe.model.document import Document
import frappe
from frappe import _
from frappe.utils import flt, cstr


class ProjectRedistributionPasedOnTimesheet(Document):
    def validate(self):
        """Validates and processes salary slips and costing summary."""
        self.validate_fields()
        self.set_salary_slip_and_rate1()
        self.create_costing_summary()

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
        """Validates required fields for Project Redistribution Pased On Timesheet."""
        required_fields = {
            "Company": self.company,
            "Account": self.account,
            "Start Date": self.from_date,
            "End Date": self.to_date,
            "Project": self.project,
        }
        missing_fields = [field for field, value in required_fields.items() if not value]
        if missing_fields:
            frappe.throw(_("Please set the following fields: {0}").format(", ".join(missing_fields)))

        # تحقق من السجل المطابق في قاعدة البيانات
        

    def set_salary_slip_and_rate1(self):
        """Fetches and sets salary slip data based on Project Redistribution Pased On Timesheet type."""
        if self.distribution_type == 'Project Redistribution Pased On Timesheet':
            
            result_cost = frappe.db.sql("""SELECT cost_center FROM `tabProject` WHERE name=%s """,(self.project), as_dict=True,)
            cost_center = result_cost[0]['cost_center'] if result_cost else None
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

            project_list = frappe.db.sql("""SELECT name FROM `tabProject Rredistribution List Pased On Timesheet`""", as_dict=True,)
            project_names = []

            for project in project_list:
                project_names.append(project['name'])

            self.employee_account_data = []

            result = frappe.db.sql(
                """
                SELECT 
                    gle.party AS employee, 
                    emp.employee_name, 
                    COALESCE(ts.total_hours, 0) AS total_hours, 
                    gle.debit,
                    gle.credit
                FROM 
                    (SELECT 
                        party, 
                        SUM(debit) AS debit,
                        SUM(credit) AS credit
                     FROM 
                        `tabGL Entry`
                     WHERE 
                        docstatus = 1
                        AND posting_date BETWEEN %s AND %s
                        AND party_type = 'Employee'
                        AND company = %s
                        AND account = %s
                        AND cost_center = %s
                        AND project = %s
                        AND is_cancelled = 0
                     GROUP BY 
                        party
                    ) AS gle
                LEFT JOIN 
                    `tabEmployee` AS emp
                ON 
                    gle.party = emp.name
                LEFT JOIN 
                    (SELECT 
                        employee, 
                        SUM(total_hours) AS total_hours 
                     FROM 
                        `tabTimesheet`
                     WHERE 
                        docstatus = 1
                        AND start_date >= %s
                        AND end_date <= %s
                        AND parent_project NOT IN %s
                     GROUP BY 
                        employee
                    ) AS ts
                ON 
                    emp.name = ts.employee;
            """,
                (self.from_date, self.to_date, self.company, self.account, cost_center, self.project, self.from_date, self.to_date, project_names), as_dict=True,
            )
            if not result:
                frappe.throw(_("No Employee in This Account"))
		
            for row in result:
                self.append('employee_account_data', {
                    'employee': row.get('employee'),
                    'employee_name': row.get('employee_name'),
                    'total': flt(row.get('debit')) - flt(row.get('credit')),
                    'total_hours': row.get('total_hours'),
                })
            

    def create_costing_summary(self):
        """Creates a costing summary for the document."""
        if self.distribution_type not in ['Employee', 'Project Redistribution Pased On Timesheet']:
            return

        self.costing_summary = []
        total_cost_of_project = 0

        for salary_data in self.employee_account_data:
            time_sheet_summary = get_time_sheet_summary(salary_data, self)
            if time_sheet_summary:
                if "employee_with_no_timesheet" in time_sheet_summary:
                    self.append(
                        "employee_with_no_timesheet",
                        {"employee": time_sheet_summary["employee_with_no_timesheet"]}
                    )
                elif "project_list" in time_sheet_summary:
                    for project in time_sheet_summary["project_list"]:
                        self.append('costing_summary', {
                            'project': project.project,
                            'employee': salary_data.employee,
                            'cost_center': project.cost_center,
                            'cost_per_hour': project.cost_per_hour,
                            'total_hours': project.total_hours,
                            'gosi_amount': project.gosi_amount,
                            'total_cost_of_project': project.total_cost_of_project,
                            'perc_distribution': project.perc_distribution,
                            'timesheets_data': project.timesheets_data,
                        })
                        total_cost_of_project += project.total_cost_of_project

        self.amount = total_cost_of_project

    @frappe.whitelist()
    def create_journal_entry(self):
        self.validate()
        precision = frappe.get_precision("Journal Entry Account", "debit_in_account_currency")
        jv = frappe.new_doc("Journal Entry")
        jv.company = self.company
        jv.posting_date = self.posting_date
        jv.user_remark = 'JV Created VIA {0}'.format(frappe.get_desk_link('Cost Distribution', self.name))

        result_cost = frappe.db.sql("""SELECT cost_center FROM `tabProject` WHERE name=%s """,(self.project), as_dict=True,)
        cost_center = result_cost[0]['cost_center'] if result_cost else None
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

        jv.append('accounts', {
			'account': self.credit_account,
			'credit_in_account_currency': flt(self.amount, precision),
            		'cost_center': cost_center,
                    'project': self.project
		})

        if not self.costing_summary:
            frappe.throw('Costing Summary Table is Empty')

        gosi_debit_sum = 0
        if self.distribution_type in ['Employee', 'Project Redistribution Pased On Timesheet']:
            for d in self.costing_summary:
                d.debit = flt(d.total_cost_of_project, precision)

            for d in self.costing_summary:
                d.gosi_debit = flt(d.gosi_amount, precision)

            gosi_debit_sum = sum([d.gosi_debit for d in self.costing_summary])

            gosi_debit_sum = sum([d.gosi_debit for d in self.costing_summary])
		

		##### if there's rounding difference in debit then appending in last row
        diff = self.amount - sum([d.debit for d in self.costing_summary]) - gosi_debit_sum
        if diff:
            for d in self.costing_summary:
                if d.idx == len(self.costing_summary):
                    d.debit += diff

        for d in self.costing_summary:
            jv.append('accounts', {
				'party': d.employee if self.distribution_type in ['Employee', 'Project Redistribution Pased On Timesheet'] else None,
				'party_type': 'Employee' if self.distribution_type in ['Employee', 'Project Redistribution Pased On Timesheet'] else None,
				'project': d.project,
				'cost_center': d.cost_center,
				'account': self.debit_account,
				'debit_in_account_currency': d.debit
			})

            if d.gosi_amount and self.distribution_type in ['Employee', 'Project Redistribution Pased On Timesheet']:
                jv.append('accounts', {
					'party': d.employee if self.distribution_type in ['Employee', 'Project Redistribution Pased On Timesheet'] else None,
					'party_type': 'Employee' if self.distribution_type in ['Employee', 'Project Redistribution Pased On Timesheet'] else None,
					'project': d.project,
					'cost_center': d.cost_center,
					'account': self.gosi_debit_account,
					'debit_in_account_currency': d.gosi_debit
				})

        jv.save()
        self.db_set('journal_entry', jv.name)


@frappe.whitelist()
def get_time_sheet_summary(salary_data, cost_dist_doc):
    employee = salary_data.employee
    total = salary_data.total
    from_date = cost_dist_doc.from_date
    to_date = cost_dist_doc.to_date
    
    project_list = frappe.db.sql("""SELECT name FROM `tabProject Rredistribution List Pased On Timesheet`""", as_dict=True)
    project_names = [project['name'] for project in project_list]
    
    from_date_1 = str(from_date) + " 00:00:01.000"
    to_date_1 = str(to_date) + " 23:59:59.995"

    data = frappe.db.sql(
        """SELECT ts.name as timesheet, tsd.project, tsd.from_time, tsd.to_time, tsd.hours, tsd.name as timesheet_child
           FROM `tabTimesheet` ts, `tabTimesheet Detail` tsd 
           WHERE ts.docstatus=1 AND ts.name = tsd.parent 
           AND ts.employee=%s 
           AND tsd.from_time >= %s AND tsd.to_time <= %s 
           AND ts.parent_project NOT IN %s""",
        (employee, from_date_1, to_date_1, project_names), as_dict=True
    )

    if not data:
        frappe.msgprint("NOT Salary Slip")
        return {"employee_with_no_timesheet": employee}

    total_hours = sum([d['hours'] for d in data])
    net_rate_per_hour = total / total_hours

    data_dict = frappe._dict()
    for d in data:
        if d.project not in data_dict:
            data_dict[d.project] = {
                'total_hours': 0, 
                'total_cost_of_project': 0, 
                'gosi_amount': 0, 
                'cost_per_hour': net_rate_per_hour, 
                'timesheets_data': []
            }
        data_dict[d.project]['total_hours'] += d.hours
        data_dict[d.project]['timesheets_data'].append({
            'timesheet': d.timesheet,
            'timesheet_child': d.timesheet_child,
            'hours': d.hours
        })

    total_cost_of_all_projects = 0
    for project, details in data_dict.items():
        details['total_cost_of_project'] = details['total_hours'] * net_rate_per_hour
        total_cost_of_all_projects += details['total_cost_of_project']

    project_list = []
    for project, details in data_dict.items():
        project_data = frappe._dict({
            'project': project, 
            'cost_per_hour': net_rate_per_hour,
            'total_hours': details['total_hours'], 
            'gosi_amount': details.get('gosi_amount', 0),  
            'timesheets_data': str(details['timesheets_data']), 
            'total_cost_of_project': details['total_cost_of_project'],
            'perc_distribution': (details['total_cost_of_project'] / (total_cost_of_all_projects or 1)) * 100
        })
        project_list.append(project_data)

    companyofpayroll = frappe.get_value("Account", cost_dist_doc.account, "company")
    for d in project_list:
        if d.get('project'):
            cost_center = frappe.get_cached_value('Project', d.get('project'), 'cost_center')
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

    if project_list:
        diff = 100 - sum([d.perc_distribution for d in project_list])
        if diff:
            project_list[-1]['perc_distribution'] += diff

    return {"project_list": project_list}

