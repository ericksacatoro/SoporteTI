#!/bin/bash
python manage.py migrate Helpdesk 0004_alter_customer_options_alter_equipment_options_and_more --fake
python manage.py migrate
python manage.py createsuperuser --noinput
gunicorn SoporteTI.wsgi:application --bind 0.0.0.0:$PORT