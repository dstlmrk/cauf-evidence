document.addEventListener("alpine:init", () => {
    Alpine.data("memberSearch", window.memberSearch);
});

function listenCitizenship() {
    const citizenshipField = document.querySelector("#id_citizenship");
    const addressFields = document.querySelector("#address-fields");
    const birthNumberFields = document.querySelector("#birth-number-fields");

    function toggleAddressFields() {
        if (citizenshipField.value === "CZ") {
            addressFields.hidden = true;
            birthNumberFields.hidden = false;
        } else {
            addressFields.hidden = false;
            birthNumberFields.hidden = true;
        }
    }

    // Initial state
    toggleAddressFields();

    // Listen to changes
    citizenshipField.addEventListener("change", toggleAddressFields);
}

// For another usage after partial page load
window.listenCitizenship = listenCitizenship;

document.body.addEventListener("showRosterDialog", (event) => {
    const { teamAtTournamentId } = event.detail;
    const rosterButton = document.getElementById(`rosterButton-${teamAtTournamentId}`);
    rosterButton.click();
});
