(function () {
    // Errors must stay until dismissed and warnings get a longer delay, so the
    // user can actually read them; success/info messages auto-hide quickly.
    function toastOptions(tags) {
        if (tags && tags.includes("error")) {
            return { autohide: false };
        }
        if (tags && tags.includes("warning")) {
            return { delay: 10000 };
        }
        return { delay: 3000 };
    }

    function createToast(message) {
        // Clone the template
        const element = htmx.find("[data-toast-template]").cloneNode(true);

        // Remove the data-toast-template attribute
        delete element.dataset.toastTemplate;

        // Set the CSS class
        element.className += " " + message.tags;

        // Set the text
        htmx.find(element, "[data-toast-body]").innerText = message.message;

        // Add the new element to the container
        htmx.find("[data-toast-container]").appendChild(element);

        // Show the toast using Bootstrap's API
        const toast = new bootstrap.Toast(element, toastOptions(message.tags));
        toast.show();
    }

    htmx.on("messages", (event) => {
        event.detail.value.forEach(createToast);
    });

    // Show all existsing toasts, except the template
    htmx.findAll(".toast:not([data-toast-template])").forEach((element) => {
        const toast = new bootstrap.Toast(element, toastOptions(element.className));
        toast.show();
    });
})();
