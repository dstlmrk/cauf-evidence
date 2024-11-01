$(document).ready(function () {
    $("#example").DataTable({
        responsive: true,
        processing: true,
        ajax: "/competitions/get",
        columns: [{ data: "name" }, { data: "season" }],
    });
});
