#!/bin/zsh
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
FRONTEND_DIR="${ROOT}/frontend"
SAMPLE_DATA_DIR="${ROOT}/sample_data"
OUT_DIR="${1:-${ROOT}/dist/silicon-agents-frontend}"

rm -rf "$OUT_DIR"
mkdir -p "$OUT_DIR" "$OUT_DIR/sample-data"

copy_page() {
  local source_name="$1"
  local target_name="$2"
  cp "${FRONTEND_DIR}/${source_name}" "${OUT_DIR}/${target_name}"
}

copy_page "index.html" "index.html"
copy_page "agent01.html" "agent01.html"
copy_page "agent02.html" "agent02.html"
copy_page "configuration.html" "configuration.html"
copy_page "history.html" "history.html"
copy_page "pilot.html" "pilot.html"
copy_page "pitch.html" "pitch.html"
copy_page "docs.html" "product-docs.html"
copy_page "pilot_access.html" "pilot-login.html"

cp "${SAMPLE_DATA_DIR}/client_profiles.json" "${OUT_DIR}/sample-data/client_profiles.json"
cp "${SAMPLE_DATA_DIR}/"* "${OUT_DIR}/sample-data/"

cat > "${OUT_DIR}/vercel.json" <<'JSON'
{
  "cleanUrls": true,
  "trailingSlash": false
}
JSON

cat > "${OUT_DIR}/README.md" <<'EOF'
# Silicon Agents Frontend Export

Static frontend bundle for Vercel deployment.

Included routes:
- `/`
- `/agent01`
- `/agent02`
- `/configuration`
- `/history`
- `/pilot`
- `/pitch`
- `/product-docs`
- `/pilot-login`

Backend configuration:
- After deployment, open `/configuration`
- Set `Deployment API Base` to the Render backend URL
- Save once so the frontend routes API calls to the deployed backend
EOF

find "$OUT_DIR" -type f | sort
