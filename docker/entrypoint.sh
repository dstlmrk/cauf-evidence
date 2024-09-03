#!/bin/sh

# collect all static files to the root directory
# python manage.py collectstatic --no-input

# start the gunicorn worker processws at the defined port
gunicorn ultihub.wsgi:application --bind 0.0.0.0:8000 &

wait
