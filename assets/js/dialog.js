function initializeModal(modalId, dialogId) {
    const modal = new bootstrap.Modal(document.getElementById(modalId));

    htmx.on("htmx:afterSwap", (e) => {
        // Response targeting the dialog element => show the modal
        if (e.detail.target.id === dialogId) {
            modal.show();

            // Update URL with roster parameter when opening large modal (roster dialog)
            if (dialogId === "dialog-lg") {
                // Extract team_at_tournament_id from the request path
                // Path format: /tournaments/team-at-tournament/123/roster-dialog
                const requestPath = e.detail.pathInfo.requestPath;
                const match = requestPath.match(/team-at-tournament\/(\d+)\//);
                if (match) {
                    const teamAtTournamentId = match[1];
                    const url = new URL(window.location);
                    url.searchParams.set("roster", teamAtTournamentId);
                    window.history.replaceState({}, "", url);
                }
            }
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

        // Remove roster parameter from URL when closing large modal
        if (dialogId === "dialog-lg") {
            const url = new URL(window.location);
            if (url.searchParams.has("roster")) {
                url.searchParams.delete("roster");
                window.history.replaceState({}, "", url);
            }
        }
    });
}

initializeModal("modal", "dialog");
initializeModal("modal-lg", "dialog-lg");
initializeModal("modal-xl", "dialog-xl");
