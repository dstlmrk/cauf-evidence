import * as Sentry from "@sentry/browser";

const dsn = document.querySelector('meta[name="sentry-dsn"]')?.content;
const environment = document.querySelector('meta[name="environment"]')?.content;
const userId = document.querySelector('meta[name="sentry-user-id"]')?.content;
const userEmail = document.querySelector('meta[name="sentry-user-email"]')?.content;

if (dsn) {
    Sentry.init({
        dsn,
        environment,
        sendDefaultPii: true,
        integrations: [],
        tunnel: "/api/feedback",
        ignoreErrors: [
            // Firefox cross-origin noise: Alpine's MutationObserver touches
            // nodes injected by browser extensions / cross-origin iframes.
            // Not an application bug and out of our control.
            "Permission denied to access property",
            // Browser extension noise: extensions calling runtime.sendMessage()
            // against a stale tab leak rejections into our global handlers.
            // Not an application bug and out of our control.
            "Invalid call to runtime.sendMessage(). Tab not found.",
        ],
    });

    if (userId) {
        Sentry.setUser({ id: userId, email: userEmail });
    }
}
