#!/bin/bash
python manage.py migrate --noinput
gunicorn SoporteTI.wsgi:application --bind 0.0.0.0:$PORT
