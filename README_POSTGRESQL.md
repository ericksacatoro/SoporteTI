# Migración a PostgreSQL - Helpdesk TI

El proyecto ha sido configurado para usar **PostgreSQL** en lugar de SQLite.

---

## Configuración automática (recomendado)

Ejecuta el script de configuración automática:

```bash
cd /home/ericksacatoro/django_proyectos/SoporteTI
./setup_postgres.sh
```

Este script:
- Instala PostgreSQL
- Crea la base de datos `helpdesk_db`
- Crea el usuario `helpdesk_user` con contraseña `helpdesk_password`
- Configura la autenticación
- Instala psycopg2-binary

---

## Configuración manual

Si prefieres configurar manualmente, consulta el archivo `POSTGRESQL_SETUP.md` que contiene instrucciones detalladas paso a paso.

---

## Después de la configuración

1. **Aplicar migraciones:**
   ```bash
   python manage.py migrate
   ```

2. **Crear superusuario:**
   ```bash
   python manage.py createsuperuser
   ```

3. **Ejecutar servidor:**
   ```bash
   python manage.py runserver
   ```

---

## Credenciales por defecto

- **Base de datos:** `helpdesk_db`
- **Usuario:** `helpdesk_user`
- **Contraseña:** `helpdesk_password`
- **Host:** `localhost`
- **Puerto:** `5432`

Puedes cambiar estas credenciales editando `SoporteTI/settings.py`.

---

## Migrar datos desde SQLite (opcional)

Si tenías datos en SQLite y quieres migrarlos a PostgreSQL:

1. **Exportar datos de SQLite:**
   ```bash
   python manage.py dumpdata --natural-foreign --natural-primary -e contenttypes -e auth.Permission --indent 2 > data_backup.json
   ```

2. **Configurar PostgreSQL** (seguir pasos anteriores)

3. **Aplicar migraciones a PostgreSQL:**
   ```bash
   python manage.py migrate
   ```

4. **Importar datos:**
   ```bash
   python manage.py loaddata data_backup.json
   ```

---

## Solución de problemas

Si encuentras errores, consulta la sección "Solución de problemas comunes" en `POSTGRESQL_SETUP.md`.

---

## Archivos modificados

- `SoporteTI/settings.py` - Configuración de DATABASES actualizada a PostgreSQL
- `requirements.txt` - Agregado psycopg2-binary

---

## Notas importantes

⚠️ **Las credenciales están hardcodeadas por simplicidad.** En producción, usa variables de entorno o archivos `.env` para mayor seguridad.

Ver la sección "Notas de seguridad" en `POSTGRESQL_SETUP.md` para implementar un manejo seguro de credenciales.
