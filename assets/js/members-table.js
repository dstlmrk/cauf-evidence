// Members table interactions without jQuery/DataTables.
//
// The list partial (#membersTable) renders a roomy desktop table and a stack of
// mobile cards from the same data, each member element carrying data-* sort and
// filter keys. This module wires column-header sorting, the search box and the
// sex/active filters in plain DOM. The partial is reloaded over HTMX after edits
// and calls initializeMembersTable() from its inline script, so we re-read the
// rows on every init and re-apply the current (module-level) sort/filter state.

// Sort comparison strategy per column key. Birthdates are emitted as YYYYMMDD
// integers so they sort by year, then month, then day via plain numeric order.
const SORT_TYPES = {
    number: "num",
    name: "text",
    birthdate: "num",
    citizenship: "text",
    licence: "num",
    email: "num",
    active: "num",
};

let sortKey = "name";
let sortDir = 1; // 1 = ascending, -1 = descending
// Favourites are pinned to the top only in the default view. As soon as the user
// sorts by a column, the pin is dropped and the list sorts purely by that column.
let userSorted = false;
let controlsBound = false;

// "number" -> "sNumber" to read the matching data-s-number attribute via dataset.
function datasetKey(key) {
    return "s" + key.charAt(0).toUpperCase() + key.slice(1);
}

function compareMembers(a, b) {
    // In the default (unsorted) view favourites float to the top; once the user
    // picks a column to sort by, ordering is governed purely by that column.
    if (!userSorted) {
        const favA = a.dataset.favourite === "1" ? 1 : 0;
        const favB = b.dataset.favourite === "1" ? 1 : 0;
        if (favA !== favB) return favB - favA;
    }

    const dk = datasetKey(sortKey);
    let va = a.dataset[dk] ?? "";
    let vb = b.dataset[dk] ?? "";

    if (SORT_TYPES[sortKey] === "num") {
        va = parseFloat(va);
        vb = parseFloat(vb);
        // Blank numbers (e.g. missing jersey number) sink to the bottom.
        if (isNaN(va)) va = -Infinity;
        if (isNaN(vb)) vb = -Infinity;
        return (va - vb) * sortDir;
    }

    return va.localeCompare(vb, undefined, { sensitivity: "base", numeric: true }) * sortDir;
}

function getRoot() {
    return document.getElementById("membersTable");
}

function getMembers(root) {
    return {
        rows: Array.from(root.querySelectorAll("[data-member-row]")),
        cards: Array.from(root.querySelectorAll("[data-member-card]")),
    };
}

// True when the member's age (data-age) falls within the selected age category's
// bounds for their sex. The bounds live on the chosen <option> as data-*-min/max
// (per sex), mirroring the AgeLimit model used across the app.
function matchesAgeCategory(el, ageOption) {
    if (!ageOption || !ageOption.value) return true;

    const age = parseFloat(el.dataset.age);
    if (isNaN(age)) return false;

    const bounds =
        el.dataset.sex === "Male"
            ? [ageOption.dataset.mMin, ageOption.dataset.mMax]
            : [ageOption.dataset.fMin, ageOption.dataset.fMax];
    return age >= parseFloat(bounds[0]) && age <= parseFloat(bounds[1]);
}

function applyFilters(root) {
    if (!root) return;

    const searchInput = document.getElementById("memberSearch");
    const sexFilter = document.getElementById("sexFilter");
    const ageFilter = document.getElementById("ageFilter");
    const licenceFilter = document.getElementById("licenceFilter");
    const activeFilter = document.getElementById("activeFilter");

    const query = (searchInput?.value || "").trim().toLowerCase();
    const sex = sexFilter?.value || "";
    const ageOption = ageFilter?.selectedOptions[0];
    const licence = licenceFilter?.value || "";
    // "Only active" is checked by default; unchecking it reveals inactive members.
    const onlyActive = activeFilter ? activeFilter.checked : true;

    const { rows, cards } = getMembers(root);
    [...rows, ...cards].forEach((el) => {
        const matchesSearch = !query || (el.dataset.search || "").toLowerCase().includes(query);
        const matchesSex = !sex || el.dataset.sex === sex;
        const matchesAge = matchesAgeCategory(el, ageOption);
        const matchesLicence = !licence || el.dataset.sLicence === licence;
        const matchesActive = !onlyActive || el.dataset.active === "1";
        el.hidden = !(matchesSearch && matchesSex && matchesAge && matchesLicence && matchesActive);
    });

    const visible = rows.some((r) => !r.hidden) || cards.some((c) => !c.hidden);
    const empty = root.querySelector("[data-members-empty]");
    if (empty) empty.hidden = visible;
}

function applySort(root) {
    if (!root) return;

    const reorder = (items) => {
        if (!items.length) return;
        const parent = items[0].parentNode;
        items
            .slice()
            .sort(compareMembers)
            .forEach((el) => parent.appendChild(el));
    };

    const { rows, cards } = getMembers(root);
    reorder(rows);
    reorder(cards);
}

function updateHeaderIndicators(root) {
    root.querySelectorAll("th.sortable").forEach((th) => {
        // Only mark a column as actively sorted once the user has chosen one, so the
        // default favourites-on-top view doesn't show a misleading sort arrow.
        if (userSorted && th.dataset.sort === sortKey) {
            th.setAttribute("aria-sort", sortDir === 1 ? "ascending" : "descending");
        } else {
            th.removeAttribute("aria-sort");
        }
    });
}

// Headers live inside the swapped partial, so they are fresh elements on every
// init; binding them each time is correct (the old ones are gone with the swap).
function bindHeaders(root) {
    root.querySelectorAll("th.sortable").forEach((th) => {
        th.addEventListener("click", () => {
            const key = th.dataset.sort;
            if (userSorted && sortKey === key) {
                sortDir = -sortDir;
            } else {
                sortKey = key;
                sortDir = 1;
            }
            // The first column click drops the favourites pin (see compareMembers).
            userSorted = true;
            updateHeaderIndicators(root);
            applySort(root);
        });
    });
    updateHeaderIndicators(root);
}

// The filter controls live in the page shell (members.html), not in the swapped
// partial, so they persist across reloads and must be bound only once.
function bindControls() {
    document.getElementById("memberSearch")?.addEventListener("input", () => applyFilters(getRoot()));
    document.getElementById("sexFilter")?.addEventListener("change", () => applyFilters(getRoot()));
    document.getElementById("ageFilter")?.addEventListener("change", () => applyFilters(getRoot()));
    document.getElementById("licenceFilter")?.addEventListener("change", () => applyFilters(getRoot()));
    document.getElementById("activeFilter")?.addEventListener("change", () => applyFilters(getRoot()));
}

// Optimistic favourite toggle: flip the star instantly with a small pop and keep
// the row's data-favourite in sync (so a later re-sort sees the new state). The
// hx-post on the button persists it on the server in the background. Delegated
// once on the document so it survives partial reloads. The button stays focused
// after click, which would leave a tooltip-like outline; blur it to keep it clean.
function bindFavouriteToggle() {
    document.addEventListener("click", (event) => {
        const button = event.target.closest(".star-toggle");
        if (!button) return;

        const nowFavourite = !button.classList.contains("is-favourite");
        button.classList.toggle("is-favourite", nowFavourite);

        const icon = button.querySelector("i");
        if (icon) {
            icon.classList.toggle("bi-star-fill", nowFavourite);
            icon.classList.toggle("bi-star", !nowFavourite);
        }
        button.setAttribute("aria-pressed", String(nowFavourite));

        // Restart the pop animation on every toggle.
        button.classList.remove("pop");
        void button.offsetWidth;
        button.classList.add("pop");

        const container = button.closest("[data-member-row], [data-member-card]");
        if (container) container.dataset.favourite = nowFavourite ? "1" : "0";

        button.blur();
    });
}

function initializeMembersTable() {
    const root = getRoot();
    if (!root) return;

    bindHeaders(root);
    if (!controlsBound) {
        bindControls();
        bindFavouriteToggle();
        controlsBound = true;
    }
    applyFilters(root);
    applySort(root);
}

// For another usage after partial page load (called from the partial's script).
window.initializeMembersTable = initializeMembersTable;
