function initializeModal(modalId, dialogId) {
    const modal = new bootstrap.Modal(document.getElementById(modalId));

    htmx.on("htmx:afterSwap", (e) => {
        // Response targeting the dialog element => show the modal
        if (e.detail.target.id === dialogId) {
            modal.show();
        }
    });

    htmx.on("htmx:beforeSwap", (e) => {
        // Empty response targeting the dialog element => hide the modal
        if (e.detail.target.id === dialogId && !e.detail.xhr.response) {
            modal.hide();
            e.detail.shouldSwap = false;
        }
    });

    // Remove dialog content after hiding
    document.getElementById(modalId).addEventListener("hidden.bs.modal", () => {
        document.getElementById(dialogId).innerHTML = "";

        // Remove GET param from URL
        const url = new URL(window.location);
        url.searchParams.delete("roster");
        history.replaceState({}, "", url);
    });
}

initializeModal("modal", "dialog");
initializeModal("modal-lg", "dialog-lg");
initializeModal("modal-xl", "dialog-xl");
