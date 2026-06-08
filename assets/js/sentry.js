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
        // Filter by the stack-frame origin: anything thrown from a browser
        // extension or injected script lives outside our app, so it's
        // environment noise, not an application bug. This generically covers
        // present and future extension errors (e.g. Safari's "askUserFor
        // permission" rejection masked as webkit-masked-url://hidden/).
        denyUrls: [
            /webkit-masked-url/, // Safari extensions / injected scripts
            /moz-extension:\/\//, // Firefox extensions
            /chrome-extension:\/\//, // Chromium extensions
            /safari-web-extension:\/\//, // Safari web extensions
        ],
        ignoreErrors: [
            // Firefox cross-origin noise: Alpine's MutationObserver touches
            // nodes injected by browser extensions / cross-origin iframes.
            // This originates in OUR own bundle, so denyUrls can't catch it
            // (the top stack frame is our URL) and a message filter is right.
            "Permission denied to access property",
            // Browser extension noise: extensions calling runtime.sendMessage()
            // against a stale tab leak rejections into our global handlers.
            // The rejection often carries no stack frame, so denyUrls may miss
            // it; keep the message filter as a belt-and-suspenders.
            "Invalid call to runtime.sendMessage(). Tab not found.",
        ],
    });

    if (userId) {
        Sentry.setUser({ id: userId, email: userEmail });
    }
}
