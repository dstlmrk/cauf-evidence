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
    });

    if (userId) {
        Sentry.setUser({ id: userId, email: userEmail });
    }
}
