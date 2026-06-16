document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll("table").forEach((table) => {
    table.setAttribute("data-readonly-snapshot", "true");
  });
});
