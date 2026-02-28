import * as Sentry from "@sentry/browser";

if (SENTRY_DSN) {
    Sentry.init({
        dsn: SENTRY_DSN,
        environment: ENVIRONMENT,
        sendDefaultPii: true,
        integrations: [],
    });
}
