#!/usr/bin/env bash
set -Eeuo pipefail
umask 077
mkdir -p "$WORKSPACE/logs" "$NEO_PERSIST_ROOT"
export DASHBOARD_PASSWORD="${DASHBOARD_PASSWORD:-}"
if [[ -z "$DASHBOARD_PASSWORD" ]]; then
  [[ -s "$NEO_PERSIST_ROOT/access-password" ]] || python -c 'import secrets;print(secrets.token_urlsafe(24))' > "$NEO_PERSIST_ROOT/access-password"
  export DASHBOARD_PASSWORD="$(cat "$NEO_PERSIST_ROOT/access-password")"
fi
[[ -s "$WORKSPACE/.jupyter_token" ]] || python -c 'import secrets;print(secrets.token_urlsafe(32))' > "$WORKSPACE/.jupyter_token"
python /opt/template/dashboard.py >> "$WORKSPACE/logs/neo-dashboard.log" 2>&1 &
python - <<'PY'
import json,os
from pathlib import Path
w=Path(os.environ['WORKSPACE'])
c={'IdentityProvider':{'token':(w/'.jupyter_token').read_text().strip()},'ServerApp':{'ip':'0.0.0.0','port':int(os.environ['JUPYTER_PORT']),'port_retries':0,'open_browser':False,'allow_root':True,'root_dir':str(w)}}
(w/'jupyter-config.json').write_text(json.dumps(c))
PY
jupyter lab --config="$WORKSPACE/jupyter-config.json" >> "$WORKSPACE/logs/jupyter.log" 2>&1 &
(
  cd /opt/forge-neo
  for dir in models outputs extensions; do
    mkdir -p "$NEO_PERSIST_ROOT/$dir"
    if [[ ! -L "$dir" ]]; then
      mkdir -p "$dir"
      rsync -a --ignore-existing "$dir/" "$NEO_PERSIST_ROOT/$dir/"
      rm -rf "$dir"
      ln -s "$NEO_PERSIST_ROOT/$dir" "$dir"
    fi
  done
  python /opt/template/download_models.py >> "$WORKSPACE/logs/neo-model-download.log" 2>&1 &
  downloader=$!
  echo "$downloader" > "$WORKSPACE/logs/neo-model-download.pid"
  if ! wait "$downloader"; then
    rm -f "$WORKSPACE/logs/neo-model-download.pid"
    echo 'One or more model downloads failed. Starting Forge anyway; check the dashboard model errors. Failed models will be retried on restart.'
  fi
  rm -f "$WORKSPACE/logs/neo-model-download.pid"
  printf 'neo:%s\n' "$DASHBOARD_PASSWORD" > "$NEO_PERSIST_ROOT/webui-auth.txt"
  exec python launch.py --listen --port "$WEBUI_PORT" --skip-install --gradio-auth-path "$NEO_PERSIST_ROOT/webui-auth.txt" --ui-settings-file "$NEO_PERSIST_ROOT/config.json" --ui-config-file "$NEO_PERSIST_ROOT/ui-config.json"
) >> "$WORKSPACE/logs/neo-container.log" 2>&1 &
trap 'jobs -pr | xargs -r kill; wait || true; exit 0' TERM INT
while true; do wait -n || true; sleep 2; done
