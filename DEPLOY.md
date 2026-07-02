# deploy runbook

The site is one box: **Hetzner CX33** (Falkenstein) at `46.224.44.127`,
domain `passingstranger.cam` (Cloudflare DNS, both A records grey-cloud /
DNS-only). ~$9.70/mo.

## the pipeline

```
edit locally → git push → server pulls → (restart if .py changed)
```

The whole thing, one command — pushes, pulls, restarts only if it must, then
proves the site is back with a health check (exits non-zero if it isn't):

```bash
./deploy.sh              # the usual
./deploy.sh --no-push    # deploy what's already on origin/main
./deploy.sh --restart    # force a restart even on a config-only change
```

Or by hand, if you'd rather watch each step:

```bash
git push origin main
ssh -i ~/.ssh/passingstranger_ed25519 root@46.224.44.127 \
  'cd /opt/passing-stranger/app && sudo -u stranger git pull && systemctl restart passing-stranger'
```

- Changed only `cams-prod.yaml` or `web/index.html`? The restart is unnecessary
  (config and page are re-read per request) — `deploy.sh` detects this and skips it.
- Changed anything in `car_stories/*.py`? Restart required (last line above).

## monitoring a deploy

No CI — `deploy.sh`'s final line (`OK … serving 200` or `FAIL …`) is your
verdict. To watch by hand:

```bash
# follow the restart live (Ctrl-C to stop)
ssh -i ~/.ssh/passingstranger_ed25519 root@46.224.44.127 'journalctl -u passing-stranger -f'
# did it come back up?
ssh -i ~/.ssh/passingstranger_ed25519 root@46.224.44.127 'systemctl status passing-stranger --no-pager'
# serving end-to-end? (app + Caddy TLS)
curl -sS -o /dev/null -w '%{http_code}\n' https://passingstranger.cam/
```

## what lives where on the server

| thing | place |
|---|---|
| app checkout | `/opt/passing-stranger/app` (runs as user `stranger`) |
| env knobs | `/etc/passing-stranger.env` (model size, session cap, curator token) |
| app service | `systemctl {status,restart} passing-stranger` · logs: `journalctl -u passing-stranger` |
| HTTPS | Caddy, `/etc/caddy/Caddyfile` (auto-renews certificates) |
| yt-dlp helper | `bgutil` service (only matters if YouTube ever unblocks live) |
| gallery clips | `/opt/passing-stranger/app/out/gallery/` (+ `order.json` = curation order) |

## rosters

- `cams.yaml` — full global roster (YouTube etc). Works **locally only**;
  YouTube/NYC-DOT block datacenter IPs.
- `cams-prod.yaml` — what the server runs (`CS_CAMS` env picks it). Only feeds
  verified reachable from the box: DelDOT + FDOT open HLS.

Adding a prod cam: find a stream (deldot.gov/map, fl511.com — DevTools →
Network → filter `m3u8`), add an entry to `cams-prod.yaml`, push, pull.
Verify it's genuinely live: grab two frames 20s apart — the pixels must change
(burned-in clocks lie).

## curator

Visit once per browser: `https://passingstranger.cam/?key=<CS_CURATOR_TOKEN>`
(token in `/etc/passing-stranger.env`). Then: ✦ clip button, ✕ delete on
hover, drag tiles to arrange.
