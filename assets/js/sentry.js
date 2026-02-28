import * as Sentry from "@sentry/browser";

const dsn = document.querySelector('meta[name="sentry-dsn"]')?.content;
const environment = document.querySelector('meta[name="environment"]')?.content;

if (dsn) {
    Sentry.init({
        dsn,
        environment,
        sendDefaultPii: true,
        integrations: [],
        tunnel: "/api/feedback/",
    });
}
