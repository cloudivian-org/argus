#!/usr/bin/env bash
# Pre-flight for an Argus demo.
#
# Regenerates the synthetic bank, runs the regression suite, prints the
# scorecard table, and tells you which alert to open with. Run this before
# standing in front of anyone.
#
#   ./scripts/demo.sh

set -euo pipefail

cd "$(dirname "$0")/.."

# The tool modules import omnigent_client, which lives in the interpreter
# Omnigent was installed under — not necessarily the system python3. Find one
# that can actually import it, starting with the interpreter behind the
# omnigent executable itself.
find_python() {
  local candidates=() shebang
  [ -n "${PYTHON:-}" ] && candidates+=("$PYTHON")
  if command -v omnigent >/dev/null 2>&1; then
    shebang="$(head -1 "$(command -v omnigent)" 2>/dev/null | sed 's|^#!||' | awk '{print $1}')"
    [ -n "$shebang" ] && candidates+=("$shebang")
  fi
  candidates+=("$HOME/.local/share/uv/tools/omnigent/bin/python" python3.13 python3.12 python3)
  for c in "${candidates[@]}"; do
    [ -n "$c" ] || continue
    if "$c" -c 'import omnigent_client' >/dev/null 2>&1; then
      echo "$c"; return 0
    fi
  done
  return 1
}

PY="$(find_python || true)"
if [ -z "$PY" ]; then
  echo "No Python found that can import omnigent_client."
  echo "Install Omnigent first:  uv tool install --python 3.12 'omnigent==0.8.2'"
  echo "Or set PYTHON=/path/to/python if you installed it elsewhere."
  exit 1
fi

echo "──────────────────────────────────────────────────────────────"
echo " Argus — AML alert triage on Omnigent"
echo "──────────────────────────────────────────────────────────────"
echo

echo "▸ Checking Omnigent…"
if ! command -v omnigent >/dev/null 2>&1; then
  echo "  omnigent is not on PATH."
  echo "  Install: uv tool install --python 3.12 'omnigent==0.8.2'"
  exit 1
fi
omnigent --version
# The bundle is tested against one release; the spec schema and policy
# handler paths are not yet stable across versions, so warn on a mismatch
# rather than let a subtle behaviour change look like an agent bug.
TESTED="0.8.2"
ACTUAL="$(omnigent --version 2>/dev/null | awk '{print $2}')"
if [ "$ACTUAL" != "$TESTED" ]; then
  echo "  NOTE: tested against Omnigent $TESTED, found $ACTUAL."
  echo "  If the spec fails to load or a policy stops attaching, pin with:"
  echo "    uv tool install --force --python 3.12 'omnigent==$TESTED'"
fi
echo

echo "▸ Checking a model credential is configured…"
# Capture first, match second. Piping into `grep -q` under `pipefail` is a
# trap: grep exits on the first match, the upstream command takes SIGPIPE,
# and pipefail turns a successful match into a failed pipeline.
CREDS="$(omnigent config list 2>/dev/null || true)"
case "$CREDS" in
  *default*) ;;
  *) echo "  No default credential found. Run: omnigent setup"; exit 1 ;;
esac
printf '%s\n' "$CREDS" | sed -n '/Credentials/,$p'
echo

echo "▸ Using Python: $PY ($("$PY" --version 2>&1))"
echo

echo "▸ Regenerating the synthetic bank sandbox…"
"$PY" scripts/generate_data.py
echo

echo "▸ Running the regression suite…"
"$PY" -m unittest discover -s tests -t . 2>&1 | tail -4
echo

echo "▸ Deterministic scorecard across the alert queue:"
"$PY" - <<'PYEOF'
import sys
from pathlib import Path
sys.path.insert(0, str(Path.cwd()))
from bankcore import scoring, store

print()
print(f"  {'ALERT':<16}{'RULE':<13}{'CUSTOMER':<32}{'SCORE':>6}  {'BAND':<9} RECOMMENDED")
print("  " + "─" * 92)
for alert in store.alerts():
    customer = store.get_customer(alert["customer_id"])
    card = scoring.score_alert(alert["alert_id"])
    print(
        f"  {alert['alert_id']:<16}{alert['detection_rule']:<13}"
        f"{customer['legal_name'][:30]:<32}{card['score']:>6}  "
        f"{card['band']:<9} {card['recommended_disposition']}"
    )
print()
PYEOF

cat <<'EOF'
──────────────────────────────────────────────────────────────
 Ready. Suggested running order:

   1. omnigent run . -p "Triage ALT-2026-0114"
      The FALSE POSITIVE. A $310k wire that is a house purchase.
      Scores 2 and closes. Open with this one — clearing noise
      correctly is the business case.

   2. omnigent run . -p "Triage ALT-2026-0117"
      Elder financial exploitation. Watch it identify the customer
      as a VICTIM, and watch it refuse to contact her.

   3. omnigent run . -p "Triage ALT-2026-0115"
      Trade-based laundering with a sanctions nexus.

 Run these INTERACTIVELY — the maker-checker policy pauses for your
 approval before anything reaches the case record. That pause is the
 control, not a bug.

 Then show the audit trail (written outside the bundle, because
 Omnigent runs each session from a temp copy of it):
   cat ~/.argus/casefiles/audit_ledger.jsonl
   omnigent run . -p "Verify the audit ledger"
──────────────────────────────────────────────────────────────
EOF
