# deploy runbook

The site is one box: **Hetzner CX33** (Falkenstein) at `46.224.44.127`,
domain `passingstranger.cam` (Cloudflare DNS, both A records grey-cloud /
DNS-only). ~$9.70/mo.

## the pipeline

```
edit locally → git push → server pulls → (restart if .py changed)
```

Concretely:

```bash
git push origin main
ssh -i ~/.ssh/passingstranger_ed25519 root@46.224.44.127 \
  'cd /opt/passing-stranger/app && sudo -u stranger git pull && systemctl restart passing-stranger'
```

- Changed only `cams-prod.yaml` or `web/index.html`? The restart is unnecessary
  (config and page are re-read per request).
- Changed anything in `car_stories/*.py`? Restart required (last line above).

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
