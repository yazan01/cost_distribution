from collections import OrderedDict
import frappe
from frappe import _, _dict
from frappe.utils import cstr, getdate, flt
from datetime import datetime, timedelta, date


def execute(filters=None):
    if not filters:
        filters = {}
    
    columns = get_columns()
    data = get_data(filters)
    
    return columns, data


def get_columns():    
    
    columns = [
        {"label": _("Company"), "fieldname": "company", "fieldtype": "Link", "options": "Company", "width": 150},
        {"label": _("Employee"), "fieldname": "employee", "fieldtype": "Link", "options": "Employee", "width": 150},
        {"label": _("Employee Name"), "fieldname": "employee_name", "fieldtype": "Data", "width": 150},
        {"label": _("Unit"), "fieldname": "custom_supporting_services__consultant", "fieldtype": "Data", "width": 150},
        {"label": _("Department"), "fieldname": "department", "fieldtype": "Data", "width": 150},
        {"label": _("Designation"), "fieldname": "designation", "fieldtype": "Link", "options": "Designation", "width": 150},
        {"label": _("Level"), "fieldname": "level", "fieldtype": "Data", "width": 150},

        {"label": _("Projects"), "fieldname": "projects", "fieldtype": "Data", "width": 150},

        {"label": _("Total CTC"), "fieldname": "total_ctc", "fieldtype": "Float", "width": 120},
        {"label": _("Total Billing"), "fieldname": "total_billing", "fieldtype": "Float", "width": 120},

        {"label": _("CTC Jan 2026"), "fieldname": "jan", "fieldtype": "Float", "width": 120},
        {"label": _("Billing Jan 2026"), "fieldname": "jan_billing", "fieldtype": "Float", "width": 120},

        {"label": _("CTC Feb 2026"), "fieldname": "feb", "fieldtype": "Float", "width": 120},
        {"label": _("Billing Feb 2026"), "fieldname": "feb_billing", "fieldtype": "Float", "width": 120},

        {"label": _("CTC Mar 2026"), "fieldname": "mar", "fieldtype": "Float", "width": 120},
        {"label": _("Billing Mar 2026"), "fieldname": "mar_billing", "fieldtype": "Float", "width": 120},

        {"label": _("CTC Apr 2026"), "fieldname": "apr", "fieldtype": "Float", "width": 120},
        {"label": _("Billing Apr 2026"), "fieldname": "apr_billing", "fieldtype": "Float", "width": 120},

        {"label": _("CTC May 2026"), "fieldname": "may", "fieldtype": "Float", "width": 120},
        {"label": _("Billing May 2026"), "fieldname": "may_billing", "fieldtype": "Float", "width": 120},

        {"label": _("CTC Jun 2026"), "fieldname": "jun", "fieldtype": "Float", "width": 120},
        {"label": _("Billing Jun 2026"), "fieldname": "jun_billing", "fieldtype": "Float", "width": 120},

        {"label": _("CTC Jul 2026"), "fieldname": "jul", "fieldtype": "Float", "width": 120},
        {"label": _("Billing Jul 2026"), "fieldname": "jul_billing", "fieldtype": "Float", "width": 120},

        {"label": _("CTC Aug 2026"), "fieldname": "aug", "fieldtype": "Float", "width": 120},
        {"label": _("Billing Aug 2026"), "fieldname": "aug_billing", "fieldtype": "Float", "width": 120},

        {"label": _("CTC Sep 2026"), "fieldname": "sep", "fieldtype": "Float", "width": 120},
        {"label": _("Billing Sep 2026"), "fieldname": "sep_billing", "fieldtype": "Float", "width": 120},

        {"label": _("CTC Oct 2026"), "fieldname": "oct", "fieldtype": "Float", "width": 120},
        {"label": _("Billing Oct 2026"), "fieldname": "oct_billing", "fieldtype": "Float", "width": 120},

        {"label": _("CTC Nov 2026"), "fieldname": "nov", "fieldtype": "Float", "width": 120},
        {"label": _("Billing Nov 2026"), "fieldname": "nov_billing", "fieldtype": "Float", "width": 120},

        {"label": _("CTC Dec 2026"), "fieldname": "dec", "fieldtype": "Float", "width": 120},  
        {"label": _("Billing Dec 2026"), "fieldname": "dec_billing", "fieldtype": "Float", "width": 120},
    ]
    
    return columns


def get_data(filters):
    conditions = get_conditions(filters)
    
    employees = frappe.db.sql("""
        SELECT 
            emp.name,
            emp.employee_name,
            emp.department,
            emp.designation,
            emp.custom_linked_level,
            emp.company,
            emp.custom_supporting_services__consultant AS unit
        FROM 
            `tabEmployee` emp
        WHERE 
            emp.status = 'Active'
            AND emp.employment_type = 'Permanent'
            {conditions}
        ORDER BY 
            emp.name
    """.format(conditions=conditions), filters, as_dict=1)

    # employees = frappe.db.sql("""
    #     SELECT 
    #         emp.name,
    #         emp.employee_name,
    #         emp.department,
    #         emp.designation,
    #         d.custom_level,
    #         emp.company,
    #         emp.custom_supporting_services__consultant AS unit
    #     FROM 
    #         `tabEmployee` emp
    #     JOIN 
    #         `tabDesignation` d
    #     ON 
    #         d.name = emp.designation 
    #     WHERE 
    #         emp.status = 'Active'
    #         AND emp.employment_type = 'Permanent'
    #         {conditions}
    #     ORDER BY 
    #         emp.name
    # """.format(conditions=conditions), filters, as_dict=1)
    
    data = []
    
    for emp in employees:
        employee_rows = get_employee_budget_data(emp, filters)
        data.extend(employee_rows)
    
    return data


def get_employee_budget_data(emp, filters):
    
    # الحصول على تخصيصات المشاريع
    project_allocations = get_employee_alocations(emp.name, emp.company, emp.custom_linked_level)
    
    # الحصول على فترات Bench
    bench_periods = get_bench_periods(emp.name, emp.company, emp.custom_linked_level, emp.unit)
    
    # دمج جميع السطور
    all_rows = []
    
    # إضافة سطور المشاريع
    for allocation in project_allocations:
        row = {
            'employee': emp.name,
            'employee_name': emp.employee_name,
            'department': emp.department,
            'designation': emp.designation,
            'level': f"{allocation['p_level']}",
            'company': emp.company,
            'custom_supporting_services__consultant': emp.unit,
            'projects': f"{allocation['project']} {allocation['project_name']} ({allocation['allocation_percentage']}%)",
            'jan': allocation.get('jan', 0),
            'feb': allocation.get('feb', 0),
            'mar': allocation.get('mar', 0),
            'apr': allocation.get('apr', 0),
            'may': allocation.get('may', 0),
            'jun': allocation.get('jun', 0),
            'jul': allocation.get('jul', 0),
            'aug': allocation.get('aug', 0),
            'sep': allocation.get('sep', 0),
            'oct': allocation.get('oct', 0),
            'nov': allocation.get('nov', 0),
            'dec': allocation.get('dec', 0),
            'total_ctc': allocation.get('total_ctc', 0),
            'jan_billing': allocation.get('jan_billing', 0),
            'feb_billing': allocation.get('feb_billing', 0),
            'mar_billing': allocation.get('mar_billing', 0),
            'apr_billing': allocation.get('apr_billing', 0),
            'may_billing': allocation.get('may_billing', 0),
            'jun_billing': allocation.get('jun_billing', 0),
            'jul_billing': allocation.get('jul_billing', 0),
            'aug_billing': allocation.get('aug_billing', 0),
            'sep_billing': allocation.get('sep_billing', 0),
            'oct_billing': allocation.get('oct_billing', 0),
            'nov_billing': allocation.get('nov_billing', 0),
            'dec_billing': allocation.get('dec_billing', 0),
            'total_billing': allocation.get('total_billing', 0)
        }
        all_rows.append(row)
    
    # إضافة سطور Bench
    for bench in bench_periods:
        row = {
            'employee': emp.name,
            'employee_name': emp.employee_name,
            'department': emp.department,
            'designation': emp.designation,
            'level': emp.custom_linked_level,
            'company': emp.company,
            'custom_supporting_services__consultant': emp.unit,
            'projects': bench['project_name'],
            'jan': bench.get('jan', 0),
            'feb': bench.get('feb', 0),
            'mar': bench.get('mar', 0),
            'apr': bench.get('apr', 0),
            'may': bench.get('may', 0),
            'jun': bench.get('jun', 0),
            'jul': bench.get('jul', 0),
            'aug': bench.get('aug', 0),
            'sep': bench.get('sep', 0),
            'oct': bench.get('oct', 0),
            'nov': bench.get('nov', 0),
            'dec': bench.get('dec', 0),
            'total_ctc': bench.get('total_ctc', 0),
            'jan_billing': bench.get('jan_billing', 0),
            'feb_billing': bench.get('feb_billing', 0),
            'mar_billing': bench.get('mar_billing', 0),
            'apr_billing': bench.get('apr_billing', 0),
            'may_billing': bench.get('may_billing', 0),
            'jun_billing': bench.get('jun_billing', 0),
            'jul_billing': bench.get('jul_billing', 0),
            'aug_billing': bench.get('aug_billing', 0),
            'sep_billing': bench.get('sep_billing', 0),
            'oct_billing': bench.get('oct_billing', 0),
            'nov_billing': bench.get('nov_billing', 0),
            'dec_billing': bench.get('dec_billing', 0),
            'total_billing': bench.get('total_billing', 0)
        }
        all_rows.append(row)
    
    return all_rows


def get_employee_alocations(employee, company, employee_level):    

    employee_alocations = frappe.db.sql("""
        SELECT 
            project, 
            project_name, 
            employee, 
            employee_name, 
            allocation_percentage,
            start_date,
            end_date
        FROM 
            `tabProject Assignment`
        WHERE 
            workflow_state = 'Approved'
            AND allocation_percentage > 0
            AND end_date >= '2026-01-01'
            AND employee = %s
        ORDER BY
            project, start_date
    """, (employee), as_dict=1)

    project_rows = []

    for d in employee_alocations:
        level_proj_ctc = 0
        level_proj_billing = 0

        # تحديد المستوى بناءً على الشركة
        if company != "iValue KSA":
            if employee_level == "Partner" and employee not in ['HR-EMP-00052', 'HR-EMP-00169']:
                level = f"{employee_level}"
            else:
                level = f"{employee_level}-R"
            # level = f"{employee_level}-R"
        else:
            level = f"{employee_level}"
                
        # محاولة الحصول على CTC من المستوى مع اللاحقة
        ctc_proj = frappe.db.sql(
            """
            SELECT ctc, billing FROM `tabLevel Rate` WHERE parent = %s AND project = %s AND year = %s
            """,
            (level, d.project, '2025'),
            as_dict=True,
        )
        
        if not ctc_proj:
            ctc_proj_4 = frappe.db.sql(
                """
                SELECT ctc, billing FROM `tabLevel Rate` WHERE parent = %s AND project IS NULL AND year = %s
                """,
                (level, '2025'),
                as_dict=True,
            )
            if not ctc_proj_4:

                ctc_proj_1 = frappe.db.sql(
                    """
                    SELECT ctc, billing FROM `tabLevel Rate` WHERE parent = %s AND project = %s AND year = %s
                    """,
                    (employee_level, d.project, '2025'),
                    as_dict=True,
                )
                if not ctc_proj_1:

                    ctc_proj_2 = frappe.db.sql(
                        """
                        SELECT ctc, billing FROM `tabLevel Rate` WHERE parent = %s AND project IS NULL AND year = %s
                        """,
                        (employee_level, '2025'),
                        as_dict=True,
                    )
                    level_proj_ctc = ctc_proj_2[0].ctc
                    level_proj_billing = ctc_proj_2[0].billing
                    show_level = employee_level
                else:
                    level_proj_ctc = ctc_proj_1[0].ctc
                    level_proj_billing = ctc_proj_1[0].billing
                    show_level = employee_level
            else:
                level_proj_ctc = ctc_proj_4[0].ctc
                level_proj_billing = ctc_proj_4[0].billing
                show_level = level
        else:
            level_proj_ctc = ctc_proj[0].ctc
            level_proj_billing = ctc_proj[0].billing
            show_level = level

        # حساب التكلفة لكل شهر
        monthly_costs = calculate_monthly_costs(
            level_proj_ctc, 
            d.allocation_percentage,
            getdate(d.get('start_date')) if d.get('start_date') else date(2026, 1, 1),
            getdate(d.end_date)
        )

        billing_months = calculate_monthly_billing(
            level_proj_billing,
            d.allocation_percentage,
            getdate(d.get('start_date')) if d.get('start_date') else date(2026, 1, 1),
            getdate(d.end_date)
        )

        
        project_row = {
            'project': d.project,
            'project_name': d.project_name,
            'allocation_percentage': d.allocation_percentage,
            'p_level' : show_level,
            'end_date': d.end_date,
            **monthly_costs,
            **billing_months
        }
        
        project_rows.append(project_row)
    
    return project_rows


def calculate_monthly_costs(monthly_ctc, allocation_percentage, start_date, end_date):
    """
    حساب التكلفة لكل شهر بناءً على أيام العمل (بدون الجمعة والسبت)
    """
    monthly_costs = {
        'jan': 0, 'feb': 0, 'mar': 0, 'apr': 0,
        'may': 0, 'jun': 0, 'jul': 0, 'aug': 0,
        'sep': 0, 'oct': 0, 'nov': 0, 'dec': 0,
        'total_ctc': 0
    }
    
    months_map = {
        1: 'jan', 2: 'feb', 3: 'mar', 4: 'apr',
        5: 'may', 6: 'jun', 7: 'jul', 8: 'aug',
        9: 'sep', 10: 'oct', 11: 'nov', 12: 'dec'
    }
    
    allocation_ratio = flt(allocation_percentage) / 100
    
    for month_num in range(1, 13):
        # تحديد بداية ونهاية الشهر
        month_start = date(2026, month_num, 1)
        
        # آخر يوم في الشهر
        if month_num == 12:
            month_end = date(2026, 12, 31)
        else:
            month_end = date(2026, month_num + 1, 1) - timedelta(days=1)
        
        # تحديد الفترة الفعلية للعمل في هذا الشهر
        period_start = max(month_start, start_date)
        period_end = min(month_end, end_date)
        
        # إذا كانت الفترة صالحة
        if period_start <= period_end:
            # حساب عدد أيام العمل في الشهر (بدون جمعة وسبت)
            total_working_days = get_working_days_in_month(2026, month_num)
            
            # حساب عدد أيام العمل في الفترة المخصصة
            allocated_working_days = get_working_days_between(period_start, period_end)
            
            # حساب التكلفة اليومية
            daily_ctc = monthly_ctc / total_working_days if total_working_days > 0 else 0
            
            # حساب التكلفة للفترة
            period_cost = daily_ctc * allocated_working_days * allocation_ratio
            
            month_key = months_map[month_num]
            monthly_costs[month_key] = period_cost
            monthly_costs['total_ctc'] += period_cost
    
    return monthly_costs


def calculate_monthly_billing(monthly_billing, allocation_percentage, start_date, end_date):
    monthly_vals = {
        'jan_billing': 0, 'feb_billing': 0, 'mar_billing': 0, 'apr_billing': 0,
        'may_billing': 0, 'jun_billing': 0, 'jul_billing': 0, 'aug_billing': 0,
        'sep_billing': 0, 'oct_billing': 0, 'nov_billing': 0, 'dec_billing': 0,
        'total_billing': 0
    }

    months_map = {
        1: 'jan_billing', 2: 'feb_billing', 3: 'mar_billing', 4: 'apr_billing',
        5: 'may_billing', 6: 'jun_billing', 7: 'jul_billing', 8: 'aug_billing',
        9: 'sep_billing', 10: 'oct_billing', 11: 'nov_billing', 12: 'dec_billing'
    }

    allocation_ratio = flt(allocation_percentage) / 100

    for month_num in range(1, 12 + 1):
        month_start = date(2026, month_num, 1)
        month_end = date(2026, month_num, 28 if month_num == 2 else (
            30 if month_num in [4,6,9,11] else 31))

        period_start = max(month_start, start_date)
        period_end = min(month_end, end_date)

        if period_start <= period_end:
            total_working = get_working_days_in_month(2026, month_num)
            allocated_working = get_working_days_between(period_start, period_end)

            daily_billing = monthly_billing / total_working if total_working > 0 else 0
            cost = daily_billing * allocated_working * allocation_ratio

            key = months_map[month_num]
            monthly_vals[key] = cost
            monthly_vals['total_billing'] += cost

    return monthly_vals




def get_working_days_in_month(year, month):
    """
    حساب عدد أيام العمل في الشهر (بدون الجمعة والسبت)
    """
    # آخر يوم في الشهر
    if month == 12:
        last_day = 31
    else:
        last_day = (date(year, month + 1, 1) - timedelta(days=1)).day
    
    working_days = 0
    for day in range(1, last_day + 1):
        current_date = date(year, month, day)
        # 4 = الجمعة، 5 = السبت
        if current_date.weekday() not in [4, 5]:
            working_days += 1
    
    return working_days


def get_working_days_between(start_date, end_date):
    """
    حساب عدد أيام العمل بين تاريخين (بدون الجمعة والسبت)
    """
    working_days = 0
    current_date = start_date
    
    while current_date <= end_date:
        # 4 = الجمعة، 5 = السبت
        if current_date.weekday() not in [4, 5]:
            working_days += 1
        current_date += timedelta(days=1)
    
    return working_days


def get_bench_periods(employee, company, employee_level, unit):
    """
    حساب فترات Bench للموظف (الفترات غير المخصصة للمشاريع)
    """
    # الحصول على جميع فترات التخصيص
    allocations = frappe.db.sql("""
        SELECT 
            start_date,
            end_date
        FROM 
            `tabProject Assignment`
        WHERE 
            workflow_state = 'Approved'
            AND allocation_percentage > 0
            AND end_date >= '2026-01-01'
            AND employee = %s
        ORDER BY
            start_date
    """, (employee), as_dict=1)
    
    # الحصول على CTC الافتراضي
    company_ctc = frappe.db.sql("""
        SELECT 
            ctc, billing
        FROM 
            `tabLevel Rate`
        WHERE 
            project IS NULL
            AND year = '2025'
            AND parent = %s
    """, (employee_level), as_dict=1)
    
    ctc_value = company_ctc[0].ctc if company_ctc else 0
    billing_value = company_ctc[0].billing if company_ctc else 0
    
    bench_rows = []
    year_start = date(2026, 1, 1)
    year_end = date(2026, 12, 31)
    
    # إذا لم يكن هناك أي تخصيص، السنة كلها Bench
    if not allocations:
        monthly_costs = calculate_monthly_costs(
            ctc_value,
            100,  # 100% allocation للـ Bench
            year_start,
            year_end
        )

        billing_costs = calculate_monthly_billing(
            billing_value, 
            100, 
            year_start,
            year_end
        )

        
        bench_rows.append({
            'project': 'Bench' if unit == 'Consultant' else 'Overhead',
            'project_name': 'Bench' if unit == 'Consultant' else 'Overhead',
            'allocation_percentage': 100,
            'end_date': year_end,
            **monthly_costs,
            **billing_costs
        })
        
        return bench_rows
    
    # فحص الفترة من بداية السنة إلى أول تخصيص
    first_allocation_start = getdate(allocations[0].get('start_date')) if allocations[0].get('start_date') else year_start
    
    if year_start < first_allocation_start:
        monthly_costs = calculate_monthly_costs(
            ctc_value,
            100,
            year_start,
            first_allocation_start - timedelta(days=1)
        )

        billing_costs = calculate_monthly_billing(
            billing_value, 
            100, 
            year_start,
            first_allocation_start - timedelta(days=1)
        )

        
        bench_rows.append({
            'project': 'Bench' if unit == 'Consultant' else 'Overhead',
            'project_name': 'Bench' if unit == 'Consultant' else 'Overhead',
            'allocation_percentage': 100,
            'end_date': first_allocation_start - timedelta(days=1),
            **monthly_costs,
            **billing_costs
        })
    
    # فحص الفجوات بين التخصيصات
    for i in range(len(allocations) - 1):
        current_end = getdate(allocations[i].end_date)
        next_start = getdate(allocations[i + 1].get('start_date')) if allocations[i + 1].get('start_date') else year_start
        
        gap_start = current_end + timedelta(days=1)
        gap_end = next_start - timedelta(days=1)
        
        if gap_start <= gap_end and gap_start <= year_end:
            monthly_costs = calculate_monthly_costs(
                ctc_value,
                100,
                gap_start,
                min(gap_end, year_end)
            )
            
            billing_costs = calculate_monthly_billing(
                billing_value, 
                100, 
                gap_start,
                min(gap_end, year_end)
            )

            bench_rows.append({
                'project': 'Bench' if unit == 'Consultant' else 'Overhead',
                'project_name': 'Bench' if unit == 'Consultant' else 'Overhead',
                'allocation_percentage': 100,
                'end_date': min(gap_end, year_end),
                **monthly_costs,
                **billing_costs
            })
    
    # فحص الفترة من آخر تخصيص إلى نهاية السنة
    last_allocation_end = getdate(allocations[-1].end_date)
    
    if last_allocation_end < year_end:
        monthly_costs = calculate_monthly_costs(
            ctc_value,
            100,
            last_allocation_end + timedelta(days=1),
            year_end
        )

        billing_costs = calculate_monthly_billing(
            billing_value, 
            100, 
            last_allocation_end + timedelta(days=1),
            year_end
        )
        
        bench_rows.append({
            'project': 'Bench' if unit == 'Consultant' else 'Overhead',
            'project_name': 'Bench' if unit == 'Consultant' else 'Overhead',
            'allocation_percentage': 100,
            'end_date': year_end,
            **monthly_costs,
            **billing_costs
        })
    
    return bench_rows


def get_conditions(filters):
    conditions = ""
    
    if filters.get("company"):
        conditions += " AND emp.company = %(company)s"

    return conditions
