#!/bin/sh

# Static files and migrations are handled by the `release` service before the
# application containers are replaced, so the start-up is just gunicorn.
# exec keeps gunicorn as PID 1 so it receives SIGTERM and shuts down gracefully
# instead of waiting for the kill timeout.
exec ddtrace-run gunicorn ultihub.wsgi:application \
    --access-logfile - \
    --error-logfile - \
    --bind 0.0.0.0:8000
