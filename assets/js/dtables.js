function initializeMembersTable() {
    $(document).ready(function () {
        const table = $("#membersTable");
        const dt = table.DataTable({
            dom: "rt",
            responsive: true,
            processing: true,
            paging: false,
            columnDefs: [
                { targets: 0, type: "num", className: "text-center" },
                { targets: 2, className: "text-start" },
                { targets: 4, searchable: true },
                { targets: 6, className: "text-start" },
                { targets: 8, orderable: false },
            ],
        });

        $("#memberSearch").on("keyup", function () {
            dt.search(this.value).draw();
        });

        $("#sexFilter").on("change", function () {
            let value = $(this).val();
            dt.column(4)
                .search(value ? "^" + value + "$" : "", true)
                .draw();
        });

        $("#activeFilter").on("change", function () {
            let isChecked = $(this).is(":checked");
            let searchValue = isChecked ? "" : "YES";
            dt.column(7).search(searchValue).draw();
        });
        // Initial filtering
        dt.column(7).search("YES").draw();

        // Be able to use htmx after DOM change (because of child rows)
        const observer = new MutationObserver(() => {
            htmx.process(document.getElementById("membersTable"));
        });
        observer.observe(document.getElementById("membersTable"), {
            childList: true,
            subtree: true,
        });

        table.css("visibility", "visible");
    });
}

// For another usage after partial page load
window.initializeMembersTable = initializeMembersTable;
