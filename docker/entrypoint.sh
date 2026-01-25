#!/bin/sh

# Compile translation message files
python manage.py compilemessages

# Collect all static files to the root directory
python manage.py collectstatic --no-input

# Apply database migrations
python manage.py migrate

# Start the gunicorn worker process at the defined port
ddtrace-run gunicorn ultihub.wsgi:application --access-logfile - --error-logfile - --bind 0.0.0.0:8000 &

wait
