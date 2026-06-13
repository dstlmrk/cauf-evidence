// Replace the native window.confirm() triggered by hx-confirm with a Bootstrap
// modal. Follows the official HTMX recipe based on the htmx:confirm event and
// issueRequest(). When the element has no hx-confirm, evt.detail.question is
// empty and we let HTMX proceed with its default behaviour.
document.addEventListener("htmx:confirm", (evt) => {
    if (!evt.detail.question) {
        return;
    }

    // Prevent the request until the user confirms it in the modal.
    evt.preventDefault();

    const modalEl = document.getElementById("confirmModal");
    const bodyEl = document.getElementById("confirmModalBody");
    const confirmBtn = document.getElementById("confirmModalConfirmBtn");
    if (!modalEl || !bodyEl || !confirmBtn) {
        // Fall back to issuing the request if the modal is missing.
        evt.detail.issueRequest(true);
        return;
    }

    bodyEl.textContent = evt.detail.question;

    const modal = bootstrap.Modal.getOrCreateInstance(modalEl);

    // One-shot confirm handler so listeners do not accumulate across uses.
    const onConfirm = () => {
        modal.hide();
        // Skip HTMX's own confirmation so the request is sent right away.
        evt.detail.issueRequest(true);
    };
    confirmBtn.addEventListener("click", onConfirm, { once: true });

    // If the modal is dismissed without confirming, drop the pending handler so
    // it cannot fire on a later, unrelated request.
    modalEl.addEventListener("hidden.bs.modal", () => confirmBtn.removeEventListener("click", onConfirm), {
        once: true,
    });

    modal.show();
});
