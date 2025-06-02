frappe.query_reports["Utilization Report"] = {
  filters: [
    {
      fieldname: "from_date",
      label: "From Date",
      fieldtype: "Date",
      default: frappe.datetime.month_start(),
      reqd: 1
    },
    {
      fieldname: "to_date",
      label: "To Date",
      fieldtype: "Date",
      default: frappe.datetime.month_end(),
      reqd: 1
    },
    {
      fieldname: "unit",
      label: "Unit",
      fieldtype: "Select",
      default: "Consultant",
      options: [
        "",
        "Supporting Services",
        "Consultant",
        "Service Provider",
        "iValue Academy",
        "Business development",
        "iValue Real Estate"
      ].join("\n")
    },
    {
      fieldname: "portfolio_type",
      label: "Portfolio Type",
      fieldtype: "Select",
      default: "NEW",
      options: [
        "",
        "NEW",
        "OLD"
      ].join("\n")
    },
    {
      fieldname: "employee_status",
      label: "Employee Status",
      fieldtype: "Select",
      default: "Active",
      options: [
        ""
        "Active",
        "Inactive",
        "Suspended",
        "Left"
      ].join("\n")
    },
    {
      fieldname: "level",
      label: "Level",
      fieldtype: "Link",
      options: "Levels"
    },
    {
      fieldname: "employee",
      label: "Employee",
      fieldtype: "Link",
      options: "Employee"
    },
    {
      fieldname: "employee_name",
      label: "Employee Name",
      fieldtype: "Data",
      read_only: 1,
      depends_on: "eval:doc.employee"
    }
  ],

  onload: function(report) {
    report.page.fields_dict.employee.$wrapper.on('change', function() {
      let emp = report.get_filter_value("employee");
      if (emp) {
        frappe.db.get_value("Employee", emp, "employee_name").then(r => {
          report.set_filter_value("employee_name", r.message.employee_name);
        });
      } else {
        report.set_filter_value("employee_name", "");
      }
    });
  }
};
