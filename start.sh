#!/bin/bash

# Recolectar archivos estáticos
python manage.py collectstatic --noinput

# Migrar con --fake para la conflictiva
python manage.py migrate Helpdesk 0004_alter_customer_options_alter_equipment_options_and_more --fake
python manage.py migrate

# Crear superusuario si no existe (usando variables de entorno)
python manage.py createsuperuser --noinput 2>/dev/null || echo "Superuser already exists or no credentials provided"

# Iniciar Gunicorn
gunicorn SoporteTI.wsgi:application --bind 0.0.0.0:$PORT