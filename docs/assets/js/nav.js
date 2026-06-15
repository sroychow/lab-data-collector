function setupNav() {
    const adminOnlyItems = document.querySelectorAll("[data-admin-only]");
    const adminLinks = document.querySelectorAll("[data-admin-link]");

    adminOnlyItems.forEach((item) => {
        item.style.display = userIsAdmin() ? "" : "none";
    });

    adminLinks.forEach((link) => {
        link.href = `${ADMIN_BASE_URL}/admin/`;
        link.target = "_blank";
        link.rel = "noopener noreferrer";
    });
}

// Run immediately if page is already loaded.
// Otherwise wait for DOMContentLoaded.
if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", setupNav);
} else {
    setupNav();
}
