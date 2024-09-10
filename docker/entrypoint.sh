#!/bin/sh

# collect all static files to the root directory
# python manage.py collectstatic --no-input

# start the gunicorn worker processws at the defined port
ddtrace-run gunicorn ultihub.wsgi:application --access-logfile - --error-logfile - --bind 0.0.0.0:8000 &

wait
