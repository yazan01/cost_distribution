frappe.query_reports["Pricing Sheet"] = {
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
