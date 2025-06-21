# Copyright (c) 2024, Furqan Asghar and contributors
# For license information, please see license.txt

from frappe.model.document import Document
import frappe
from frappe import _
from frappe.utils import flt, cstr
from datetime import datetime, timedelta

class CTCDistribution(Document):
    def validate(self):
        """Validates and processes salary slips and costing summary."""
        self.validate_fields()
        self.set_salary_slip_and_rate1()
        self.create_costing_summary()
        # Apply project-specific CTC rates during validation
        self.apply_project_specific_ctc_rates()

    def on_submit(self):
        """Validate projects for employees with no timesheet"""
        for timesheet in self.add_project_for_employee_no_timesheet:
            if not timesheet.project:
                frappe.throw(_("Please add project for employee {0}").format(timesheet.employee))
        
    def validate_fields(self):
        required_fields = {
            "Company": self.company,
            "Start Date": self.from_date,
            "End Date": self.to_date,
        }
        missing_fields = [field for field, value in required_fields.items() if not value]
        if missing_fields:
            frappe.throw(_("Please set the following fields: {0}").format(", ".join(missing_fields)))

    def set_salary_slip_and_rate1(self):
        from_date_obj = datetime.strptime(self.from_date, '%Y-%m-%d')
        year = from_date_obj.year
        
        start_date = datetime.strptime(self.from_date, '%Y-%m-%d')
        end_date = datetime.strptime(self.to_date, '%Y-%m-%d')

        current_date = start_date
        number_of_days = 0

        while current_date <= end_date:
            if current_date.weekday() not in (4, 5):
                number_of_days += 1
            current_date += timedelta(days=1)

        """Fetches and sets CTC data based on CTC distribution type."""
        if self.distribution_type == 'CTC Distribution':
            self.employee_ctc_data = []

            result = frappe.db.sql(
                """
                SELECT 
                    emp.name AS employee, 
                    emp.employee_name, 
                    emp.company, 
                    emp.employment_type, 
                    emp.designation, 
                    des.custom_level, 
                    COALESCE(lr.ctc, NULL) AS ctc, 
                    COALESCE(ts.total_hours, 0) AS total_hours
                FROM 
                    (SELECT 
                        name, 
                        employee_name, 
                        company, 
                        employment_type, 
                        designation, 
                        date_of_joining, 
                        relieving_date 
                    FROM 
                        `tabEmployee`
                    WHERE 
                        company = %s
                        AND employment_type = 'Permanent'
                        AND date_of_joining <= %s
                        AND (relieving_date IS NULL OR relieving_date > %s)
                    ) AS emp
                LEFT JOIN 
                    (SELECT 
                        name, 
                        custom_level 
                    FROM 
                        `tabDesignation`
                    ) AS des
                ON 
                    emp.designation = des.name
                LEFT JOIN 
                    (SELECT 
                        parent, 
                        ctc 
                    FROM 
                        `tabLevel Rate`
                    WHERE 
                        year = %s AND project IS NULL
                    ) AS lr
                ON 
                    des.custom_level = lr.parent
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
                    GROUP BY 
                        employee
                    ) AS ts
                ON 
                    emp.name = ts.employee;
            """,
                (self.company, self.to_date, self.from_date, year, self.from_date, self.to_date), as_dict=True,
            )

            result2 = frappe.db.sql(
                """
                SELECT 
                    emp.name AS employee, 
                    emp.employee_name, 
                    emp.company, 
                    emp.employment_type, 
                    emp.designation, 
                    des.custom_level, 
                    COALESCE(emp.ctc, NULL) AS ctc, 
                    COALESCE(ts.total_hours, 0) AS total_hours
                FROM 
                    (SELECT 
                        name, 
                        employee_name, 
                        ctc,
                        company, 
                        employment_type, 
                        designation, 
                        date_of_joining, 
                        relieving_date 
                    FROM 
                        `tabEmployee`
                    WHERE 
                        company = %s
                        AND employment_type = 'Subcontract'
                        AND date_of_joining <= %s
                        AND (relieving_date IS NULL OR relieving_date > %s)
                    ) AS emp
                LEFT JOIN 
                    (SELECT 
                        name, 
                        custom_level 
                    FROM 
                        `tabDesignation`
                    ) AS des
                ON 
                    emp.designation = des.name
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
                    GROUP BY 
                        employee
                    ) AS ts
                ON 
                    emp.name = ts.employee;
            """,
                (self.company, self.to_date, self.from_date, self.from_date, self.to_date), as_dict=True,
            )
            
            employee_with_no_ctc = []

            for row in result:
                if flt(row.get('ctc')) == 0:
                    employee_with_no_ctc.append(row.get('employee'))

            for row in result2:
                if flt(row.get('ctc')) == 0:
                    employee_with_no_ctc.append(row.get('employee'))
            
            if employee_with_no_ctc:
                frappe.throw(_("Please set CTC for the following employees: {0}").format(", ".join(employee_with_no_ctc)))
            
            for row in result:
                if row.get('total_hours') == 0 and not any(entry.get('employee') == row.get('employee') for entry in self.get('add_project_for_employee_no_timesheet', []) ):
                    self.append(
                        "add_project_for_employee_no_timesheet",
                        {"employee": row.get('employee')}
                    )

            for row in result2:
                if row.get('total_hours') == 0 and not any(entry.get('employee') == row.get('employee') for entry in self.get('add_project_for_employee_no_timesheet', []) ):
                    self.append(
                        "add_project_for_employee_no_timesheet",
                        {"employee": row.get('employee')}
                    )
            
            for row in result:
                self.append('employee_ctc_data', {
                    'employee': row.get('employee'),
                    'employee_name': row.get('employee_name'),
                    'employment_type': row.get('employment_type'),
                    'designation': row.get('designation'),
                    'level': row.get('custom_level'),
                    'ctc': flt( (flt(row.get('ctc'))/flt(number_of_days * 9)) * flt(row.get('total_hours')) ) if row.get('total_hours') > 0 else flt(row.get('ctc')),
                    'total_hours': row.get('total_hours'),
                })
            
            for row in result2:
                self.append('employee_ctc_data', {
                    'employee': row.get('employee'),
                    'employee_name': row.get('employee_name'),
                    'employment_type': row.get('employment_type'),
                    'designation': row.get('designation'),
                    'level': row.get('custom_level'),
                    'ctc': flt(row.get('ctc')),
                    'total_hours': row.get('total_hours'),
                })

    def apply_project_specific_ctc_rates(self):
        """Apply project-specific CTC rates and update costs accordingly"""
        if not self.posting_date:
            return
            
        posting_date = frappe.utils.getdate(self.posting_date)
        fiscal_year = str(posting_date.year)
        
        updated = False
        results = []

        for emp_row in self.employee_ctc_data:
            if emp_row.employment_type != "Permanent":
                continue

            employee = emp_row.employee
            level = emp_row.level

            for cost_row in self.costing_summary:
                if cost_row.employee != employee:
                    continue

                project = cost_row.project

                try:
                    level_doc = frappe.get_doc("Levels", level)
                except:
                    continue

                matched_ctc = None
                for rate_row in level_doc.rate:
                    if rate_row.year == fiscal_year and rate_row.project == project:
                        matched_ctc = rate_row.ctc
                        break

                if matched_ctc is not None:
                    new_cost = (matched_ctc * cost_row.perc_distribution) / 100
                    cost_row.total_cost_of_project = new_cost
                    results.append(
                        f"Employee: {employee} | Project: {project} | Level: {level} | CTC: {matched_ctc} | New Cost: {new_cost}"
                    )
                    updated = True

        if updated:
            # Update Amount (sum of all total_cost_of_project)
            self.amount = sum(row.total_cost_of_project for row in self.costing_summary if row.total_cost_of_project)

            # Update employee_ctc_data.ctc per employee
            for emp_row in self.employee_ctc_data:
                emp = emp_row.employee
                total = sum(row.total_cost_of_project for row in self.costing_summary if row.employee == emp)
                emp_row.ctc = total
            
            if results and frappe.flags.in_request:
                frappe.msgprint(f"Applied project-specific CTC rates for {len(results)} entries")

    @frappe.whitelist()
    def create_costing_summary(self):
        """Creates a costing summary for the document."""
        if self.distribution_type not in ['Employee', 'CTC Distribution']:
            return

        self.costing_summary = []
        total_cost_of_project = 0

        for salary_data in self.employee_ctc_data:
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
                            'total_cost_of_project': project.total_cost_of_project,
                            'perc_distribution': project.perc_distribution,
                            'timesheets_data': project.timesheets_data,
                        })
                        total_cost_of_project += project.total_cost_of_project
        
        self.amount = total_cost_of_project

@frappe.whitelist()
def get_time_sheet_summary(salary_data, cost_dist_doc):
    employee = salary_data.employee
    total = salary_data.ctc
    from_date = cost_dist_doc.from_date
    to_date = cost_dist_doc.to_date

    from_date_1 = str(from_date) + " 00:00:01.000"
    to_date_1 = str(to_date) + " 23:59:59.995"

    data_dict = frappe._dict()

    # Fetch timesheet data
    data = frappe.db.sql(
        """
        SELECT ts.name as timesheet, tsd.project, tsd.from_time, tsd.to_time, tsd.hours, tsd.name as timesheet_child
        FROM `tabTimesheet` ts, `tabTimesheet Detail` tsd 
        WHERE ts.docstatus=1 AND ts.name = tsd.parent AND ts.employee=%s 
        AND tsd.from_time >= %s AND tsd.to_time <= %s
        """,
        (employee, from_date_1, to_date_1),
        as_dict=True,
    )

    if not data:
        project = None
        for RY in cost_dist_doc.add_project_for_employee_no_timesheet:
            if RY.employee == employee:
                project = RY.project
        if project == None:
            return {"employee_with_no_timesheet": employee}
        hours = 1
        net_rate_per_hour = total / hours

        data_dict.setdefault(project, {
            'total_hours': 1,
            'total_cost_of_project': total,
            'cost_per_hour': net_rate_per_hour,
            'timesheets_data': []
        })
    else:
        hours = sum([d.hours for d in data])
        net_rate_per_hour = total / hours

        for d in data:
            data_dict.setdefault(d.project, {
                'total_hours': 0,
                'total_cost_of_project': 0,
                'cost_per_hour': net_rate_per_hour,
                'timesheets_data': []
            })

            data_dict[d.project]['total_hours'] += d.hours
            data_dict[d.project]['timesheets_data'].append({
                'timesheet': d.timesheet,
                'timesheet_child': d.timesheet_child,
                'hours': d.hours
            })

    # Calculate total cost of all projects
    total_cost_of_all_projects = 0
    for d in data_dict:
        data_dict[d]['total_cost_of_project'] = data_dict[d]['total_hours'] * net_rate_per_hour
        total_cost_of_all_projects += data_dict[d]['total_cost_of_project']

    # Prepare project list
    project_list = []
    for k, v in data_dict.items():
        project_list.append(frappe._dict({
            'project': k,
            'cost_per_hour': net_rate_per_hour,
            'total_hours': data_dict[k]['total_hours'],
            'timesheets_data': cstr(data_dict[k]['timesheets_data']),
            'total_cost_of_project': data_dict[k]['total_cost_of_project'],
            'perc_distribution': (data_dict[k]['total_cost_of_project'] / (total_cost_of_all_projects or 1)) * 100
        }))

    # Update cost center based on company
    company_of_payroll = cost_dist_doc.company
    for d in project_list:
        if d.get('project'):
            cost_center = frappe.get_cached_value('Project', d.get('project'), 'cost_center')

            last_dash_index = cost_center.rfind('-')
            if last_dash_index != -1:
                cost_center = cost_center[:last_dash_index].strip()

            if company_of_payroll == "iValueJOR":
                cost_center += " - iJOR"
            elif company_of_payroll == "iValueUAE":
                cost_center += " - iUAE"
            elif company_of_payroll == "iValue KSA":
                cost_center += " - iKSA"
            else:
                cost_center += " - iV"

            d['cost_center'] = cost_center

    # Handle rounding difference
    if project_list:
        diff = 100 - sum([d.perc_distribution for d in project_list])
        if diff:
            project_list[-1]['perc_distribution'] += diff

    return {"project_list": project_list}
