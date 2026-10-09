#!/usr/bin/env bash
set -Eeuo pipefail
IMAGE="${1:?image tag required}"
REPORT_DIR="${REPORT_DIR:-$PWD/ltx23-test-results}"
mkdir -p "$REPORT_DIR"
CID=""
cleanup() {
  if [[ -n "$CID" ]]; then
    docker logs "$CID" > "$REPORT_DIR/docker.log" 2>&1 || true
    docker cp "$CID:/workspace/logs" "$REPORT_DIR/" || true
    docker cp "$CID:/tmp/ltx23-runtime" "$REPORT_DIR/runtime" || true
    docker rm -f "$CID" >/dev/null || true
  fi
}
trap cleanup EXIT
# No GPU attached: a ComfyUI failure must not take dashboard/Jupyter/container down.
CID="$(docker run -d -e DOWNLOAD_WORKFLOW_MODELS=0 -p 127.0.0.1:18080:18080 -p 127.0.0.1:8888:8888 "$IMAGE")"
for i in $(seq 1 120); do
  if curl -fsS http://127.0.0.1:18080/api/health > "$REPORT_DIR/health.json"; then break; fi
  sleep 1
done
curl -fsS http://127.0.0.1:18080/api/health
for i in $(seq 1 120); do
  if docker exec "$CID" python -c "import socket; socket.create_connection(('127.0.0.1',8888),2)"; then break; fi
  sleep 1
done
docker exec "$CID" python -c "import socket; socket.create_connection(('127.0.0.1',8888),2)"
sleep 5
test "$(docker inspect "$CID" --format '{{.State.Running}}')" = true
test "$(docker inspect "$CID" --format '{{.RestartCount}}')" = 0
curl -fsS http://127.0.0.1:18080/api/status > "$REPORT_DIR/status.json"
docker cp "$CID:/opt/ltx23/build_report.json" "$REPORT_DIR/build_report.json"
docker image inspect "$IMAGE" --format '{{.Size}}' > "$REPORT_DIR/image-size-bytes.txt"
cleanup
CID=""
# Separate CPU launch validates actual registered node types, without model downloads.
CID="$(docker run -d -e DOWNLOAD_WORKFLOW_MODELS=0 -e ENABLE_JUPYTER=0 -e COMFY_EXTRA_ARGS=--cpu "$IMAGE")"
for i in $(seq 1 180); do
  if docker exec "$CID" python /opt/ltx23/validate_workflow.py --nodes-only > "$REPORT_DIR/node-validation.log" 2>&1; then
    echo 'CPU node registration validation passed'
    exit 0
  fi
  # Once object_info responds, ComfyUI has finished importing nodes: fail immediately.
  if docker exec "$CID" python -c "import json; r=json.load(open('/tmp/ltx23-runtime/validation.json')); assert r.get('missing_backend_nodes') is not None" 2>/dev/null; then
    cat "$REPORT_DIR/node-validation.log"
    docker exec "$CID" tail -n 160 /workspace/logs/comfy.log || true
    exit 1
  fi
  if docker exec "$CID" python -c "import json; s=json.load(open('/tmp/ltx23-runtime/services.json')); assert s['comfy']['state']=='Error'" 2>/dev/null; then
    cat "$REPORT_DIR/node-validation.log"
    exit 1
  fi
  sleep 1
done
cat "$REPORT_DIR/node-validation.log"
exit 1
