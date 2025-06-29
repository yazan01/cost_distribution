frappe.query_reports["Pricing Sheet"] = {
  filters: [
    {
      fieldname: "project",
      label: "Project",
      fieldtype: "Link",
      option: "Project"
      reqd: 1
    }
  ]  
};
