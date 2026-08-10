#!/usr/bin/env bash
# Bring the Argus demo up in the Omnigent GUI, from cold.
#
#   ./scripts/start_gui.sh              # server + one seeded triage
#   ./scripts/start_gui.sh 0117 0115    # server + these alerts seeded
#
# Then open http://localhost:6767 (or point the desktop app there via the
# Server menu) and pick the session in the sidebar.

set -uo pipefail

BUNDLE="$(cd "$(dirname "$0")/.." && pwd)"
OMNI="${OMNI:-$HOME/.local/bin/omnigent}"
URL="http://127.0.0.1:6767"

# Alerts to seed. Default is the false positive — the one to open a demo with.
ALERTS=("$@")
[ ${#ALERTS[@]} -eq 0 ] && ALERTS=("0114")

echo "──────────────────────────────────────────────────────────────"
echo " Argus demo — GUI startup"
echo "──────────────────────────────────────────────────────────────"

command -v "$OMNI" >/dev/null 2>&1 || { echo "omnigent not found at $OMNI"; exit 1; }

# The server MUST start from outside the Omnigent source checkout. Started
# from inside one, it serves that repo's unbuilt web/ directory and the
# browser shows "web UI isn't installed" instead of the bundled UI.
echo "▸ Starting the server from \$HOME (never from the omnigent checkout)…"
cd "$HOME" || exit 1
"$OMNI" server --background 2>&1 | tail -2

# A DB stamped by a newer Omnigent (e.g. the desktop app) makes the CLI
# server fail its alembic migration. Move it aside and let a fresh one build.
if ! curl -sf -o /dev/null "$URL/"; then
  echo "▸ Server did not come up — moving a mismatched chat.db aside and retrying…"
  [ -f "$HOME/.omnigent/chat.db" ] && \
    mv "$HOME/.omnigent/chat.db" "$HOME/.omnigent/chat.db.stale-$(date +%Y%m%d-%H%M%S)"
  "$OMNI" server --background 2>&1 | tail -2
fi

curl -sf -o /dev/null "$URL/" || { echo "Server still down. Check ~/.omnigent/logs/server/"; exit 1; }

if curl -s "$URL/" | grep -qi "web UI not installed"; then
  echo "  WARNING: server is serving the API-only page."
  echo "  It was started from inside an omnigent source checkout. Stop it and rerun this script."
  exit 1
fi
echo "  Server up at $URL, serving the real web UI."

echo "▸ Seeding triage sessions: ${ALERTS[*]}"
for id in "${ALERTS[@]}"; do
  alert="ALT-2026-${id}"
  echo "    $alert …"
  "$OMNI" run "$BUNDLE" -p "Triage $alert end to end." \
    </dev/null >"/tmp/argus-$alert.log" 2>&1 &
  sleep 5   # stagger so the sessions register in a readable order
done

cat <<EOF

──────────────────────────────────────────────────────────────
 Open the GUI:

   open $URL

 Or in the desktop app: Server menu → connect to $URL
 (do NOT let the app spawn its own server — it ships a newer
  build that re-stamps chat.db and breaks this CLI server)

 The seeded sessions appear in the left sidebar as they start.
 Each takes a few minutes; sub-agents show in the right panel.

 To triage another alert, just type it into an existing
 session's composer — it is already bound to Argus:

   "Triage ALT-2026-0116"

 Alerts: 0113 structuring · 0114 FALSE POSITIVE · 0115 trade-based
         0116 mule · 0117 elder victim · 0118 PEP layering
──────────────────────────────────────────────────────────────
EOF
