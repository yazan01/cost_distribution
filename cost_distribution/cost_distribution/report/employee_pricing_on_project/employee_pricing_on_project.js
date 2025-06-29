frappe.query_reports["Employee Pricing On Project"] = {
  filters: [
    {
      fieldname: "project",
      label: "Project",
      fieldtype: "Link",
      options: "Project",
      reqd: 1
    }
  ]
};