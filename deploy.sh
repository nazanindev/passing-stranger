#!/usr/bin/env bash
#
# deploy.sh — push local main, pull it on the box, restart if code changed,
# then prove the site is actually serving. One command, decent logs.
#
#   ./deploy.sh              # push + pull + (restart if *.py changed) + health check
#   ./deploy.sh --no-push    # skip the local push (deploy what's already on origin)
#   ./deploy.sh --restart    # force a restart even if only config/page changed
#
# Reads the box details from DEPLOY.md's runbook. Exits non-zero if the site
# doesn't come back with 200 — so you can trust the last line.

set -euo pipefail

HOST="root@46.224.44.127"
KEY="$HOME/.ssh/passingstranger_ed25519"
APP="/opt/passing-stranger/app"
SERVICE="passing-stranger"
URL="https://passingstranger.cam/"
SSH=(ssh -i "$KEY" -o ConnectTimeout=10 "$HOST")

PUSH=1
FORCE_RESTART=0
for arg in "$@"; do
  case "$arg" in
    --no-push) PUSH=0 ;;
    --restart) FORCE_RESTART=1 ;;
    *) echo "unknown flag: $arg" >&2; exit 2 ;;
  esac
done

# --- pretty logging -----------------------------------------------------------
if [ -t 1 ]; then B=$'\033[1m'; DIM=$'\033[2m'; GRN=$'\033[32m'; RED=$'\033[31m'; YLW=$'\033[33m'; Z=$'\033[0m'
else B=""; DIM=""; GRN=""; RED=""; YLW=""; Z=""; fi
say()  { printf '%s[%s]%s %s\n' "$DIM" "$(date +%H:%M:%S)" "$Z" "$*"; }
step() { printf '\n%s== %s ==%s\n' "$B" "$*" "$Z"; }
die()  { printf '%s[%s] FAIL:%s %s\n' "$RED" "$(date +%H:%M:%S)" "$Z" "$*" >&2; exit 1; }

# --- 0. sanity ----------------------------------------------------------------
step "preflight"
branch="$(git rev-parse --abbrev-ref HEAD)"
[ "$branch" = "main" ] || die "on branch '$branch', deploy runs from main"
[ -f "$KEY" ] || die "ssh key not found: $KEY"
local_head="$(git rev-parse --short HEAD)"
say "local main at $local_head"

# --- 1. push ------------------------------------------------------------------
if [ "$PUSH" = 1 ]; then
  step "push origin main"
  git push origin main
else
  say "${YLW}--no-push:${Z} deploying whatever is already on origin/main"
fi

# --- 2. pull on the box + decide whether a restart is needed ------------------
step "pull on the server"
# All git runs as 'stranger' (repo owner); the remote emits one line
# "<old> <new> <changed,files,>" so we can decide about the restart. $APP is
# passed as an argument so the heredoc can stay fully quoted (no escaping).
result="$("${SSH[@]}" bash -s "$APP" <<'REMOTE'
set -e
cd "$1"
old=$(sudo -u stranger git rev-parse HEAD)
sudo -u stranger git pull --ff-only >/tmp/deploy-pull.log 2>&1
new=$(sudo -u stranger git rev-parse HEAD)
changed=$(sudo -u stranger git diff --name-only "$old" "$new" | tr '\n' ',')
echo "${old:0:7} ${new:0:7} ${changed:-none}"
REMOTE
)"
read -r OLD NEW CHANGED <<<"$result"
say "server ${OLD} → ${NEW}"

if [ "$OLD" = "$NEW" ]; then
  say "${YLW}nothing new pulled${Z} (server already at $NEW)"
else
  say "changed: ${CHANGED%,}"
fi

need_restart=0
[ "$FORCE_RESTART" = 1 ] && need_restart=1
# a .py change requires a restart; config (*.yaml) and web/index.html are
# re-read per request, so they don't
case "$CHANGED" in
  *car_stories/*.py*) need_restart=1 ;;
esac

# --- 3. restart (only if warranted) ------------------------------------------
if [ "$need_restart" = 1 ]; then
  step "restart $SERVICE"
  "${SSH[@]}" "systemctl restart $SERVICE"
  say "restart issued"
else
  step "restart skipped"
  say "no *.py change and no --restart — config/page are re-read live"
fi

# --- 4. service state + recent logs ------------------------------------------
step "service state"
"${SSH[@]}" "systemctl is-active $SERVICE && systemctl --no-pager -p ActiveState,SubState,ExecMainStartTimestamp show $SERVICE | sed 's/^/  /'" \
  || die "$SERVICE is not active — see logs below"

step "recent logs (last 30 lines)"
"${SSH[@]}" "journalctl -u $SERVICE -n 30 --no-pager"

# --- 5. end-to-end health check ----------------------------------------------
step "health check → $URL"
code=""
for i in $(seq 1 12); do
  code="$(curl -sS -o /dev/null -w '%{http_code}' --max-time 10 "$URL" || echo 000)"
  [ "$code" = "200" ] && break
  say "attempt $i: HTTP $code — retrying"
  sleep 3
done

if [ "$code" = "200" ]; then
  printf '\n%s[%s] OK:%s %s serving 200 · server at %s\n' \
    "$GRN" "$(date +%H:%M:%S)" "$Z" "$URL" "$NEW"
else
  die "site did not return 200 (last: HTTP $code). Check: ${SSH[*]} 'journalctl -u $SERVICE -n 80 --no-pager'"
fi
