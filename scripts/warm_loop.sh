#!/usr/bin/env bash
# Precalienta las pantallas cada WARM_INTERVAL segundos (600 por defecto).
#
# warm_cache llena la cache del equipo donde corre. Con la cache de archivos
# de Django (.cache/) tiene que correr en el MISMO contenedor que gunicorn:
# se lanza en segundo plano desde el arranque (startup.sh), por ejemplo:
#
#     bash scripts/warm_loop.sh &
#     exec gunicorn ...
#
# Si una pasada tarda mas que el intervalo, la siguiente espera: nunca se
# solapan. Un fallo se registra y el ciclo continua.
set -uo pipefail

cd "$(dirname "$0")/.."
PYTHON="${PYTHON:-python}"
INTERVAL="${WARM_INTERVAL:-600}"
FIRST_DELAY="${WARM_FIRST_DELAY:-60}"   # deja arrancar a la aplicacion

sleep "$FIRST_DELAY"
while true; do
  started=$(date +%s)
  if ! "$PYTHON" manage.py warm_cache; then
    echo "warm_cache fallo ($(date -u +%FT%TZ)); se reintenta en el siguiente ciclo" >&2
  fi
  elapsed=$(( $(date +%s) - started ))
  wait_for=$(( INTERVAL - elapsed ))
  if [ "$wait_for" -gt 0 ]; then sleep "$wait_for"; fi
done
