#!/usr/bin/env bash
# Ejecuta una tarea programada del panel. Sirve para cron dentro del
# contenedor, Azure Container Instances / Container Apps Job, un CronJob de
# Kubernetes o un pipeline: todos llaman al mismo script.
#
#   horario      cada hora:      hojas de Sheets, Azure DevOps y catalogos
#   diario       cada dia 06:00: horas de Clockify y catalogos
#   precalentar  cada 10 min:    precalienta las pantallas (debe correr donde
#                                vive la cache de la aplicacion)
#   revisar      cada hora:      falla si algo esta atrasado
#
# Variables: PYTHON (por defecto "python"). Lee el resto del .env o del
# entorno (DATABASE_URL, CLOCKIFY_*, AZURE_DEVOPS_*, GOOGLE_*...).
set -euo pipefail

cd "$(dirname "$0")/.."
PYTHON="${PYTHON:-python}"

case "${1:-}" in
  horario)     exec "$PYTHON" manage.py sync_datastore --pasos hojas,azure,lecturas,catalogos,eva ;;
  diario)      exec "$PYTHON" manage.py sync_datastore --pasos clockify,catalogos,eva ;;
  precalentar) exec "$PYTHON" manage.py warm_cache ;;
  revisar)     exec "$PYTHON" manage.py check_datastore --lecturas ;;
  eva-captura) exec "$PYTHON" manage.py close_eva_month --capture ;;
  eva-cierre)  exec "$PYTHON" manage.py close_eva_month ;;
  *)
    echo "Uso: $0 {horario|diario|precalentar|revisar|eva-captura|eva-cierre}" >&2
    exit 2
    ;;
esac
