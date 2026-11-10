# One experience over a private connection

Everyone opens the same `/` URL. There are no separate player, projector, station or facilitator pages. Each device progresses independently; shared laptops use Reset between people.

The Fury stays in the data center. No app command changes Tailscale, firewall or WiFi, and no public port is added. The preexisting public :443 mapping still forwards the older :8080 app; leave it untouched and do not use it for this private :8090 experience.

## A private laptop

On a laptop with tailnet/SSH access to the Fury:

```bash
ssh -N -L 8090:127.0.0.1:8090 gb300@100.87.127.125
```

Keep that terminal open and visit **http://127.0.0.1:8090/**. Each prepared tailnet laptop can use its own forward and the same URL. A phone cannot use a laptop’s loopback address; use a room hub for ordinary phones.

Private Tailscale Serve was explicitly authorized and configured on 2026-11-09:

**https://hp-zgx-fury-showcase.taild25e44.ts.net:8443/**

Visitors must have Tailscale connected and permission to reach this device. No SSH forward is needed for this URL. HTTPS 8443 proxies the upgraded loopback :8090 app and runs in the background. Serve configuration confirms no Funnel allowance for this endpoint. The existing public :443 mapping still points to the older :8080 app; use the full URL including `:8443` for the upgrade.

The real HTTPS browser check passed live WebSocket progress, Deploy, owner Reset and the Share URL/QR with zero console errors. Proof: `docs/private-tailscale-access.json`. The existing model services and app processes were not restarted or changed for this routing update.

To restore only this private endpoint if needed:

```bash
tailscale serve --bg --https=8443 --yes http://127.0.0.1:8090
```

To remove only this endpoint:

```bash
tailscale serve --https=8443 off
```

Do not reset all Serve configuration or change the existing :443 handler. The pre-change configuration is backed up privately under `~/siege/backup/tailscale-before-private-siege-*.json`.

## Room hub for ordinary phones

Use a tailnet-connected laptop on a dedicated room LAN/travel router where possible. Conference WiFi often blocks device-to-device traffic. The app does not configure the LAN or firewall.

1. On the Fury, run `cd ~/cyber_siege` and `./siege start`.
2. On the hub laptop, open the SSH forward above, or use a separately verified private Serve upstream.
3. Install `requirements-relay.txt` in a local Python environment with this repo’s standalone relay modules. No GPU or model is required on the hub.
4. Check and start the relay, replacing the example address with the laptop’s actual private LAN IP:

```bash
python -m revamp.relay --upstream http://127.0.0.1:8090 --check
python -m revamp.relay --upstream http://127.0.0.1:8090 --listen 192.168.8.20 --port 8095
```

5. On every phone, table laptop and presentation browser, open **http://192.168.8.20:8095/**. This is the same page for everyone. Share experience copies the browser-visible root URL, with no session credentials or room code.
6. For operator status output to show that same address, restart only the managed web app on the Fury with the existing private URL configured:

```bash
cd ~/cyber_siege
./siege stop
SIEGE_BASE_URL=http://192.168.8.20:8095 ./siege start
```

This does not change the loopback binding or model services. It changes the displayed base URL only. Private Serve users can configure their verified private HTTPS URL in the same way.

The hub accepts a fixed private upstream and a specific private interface. It cannot be a general forward proxy and will not bind a wildcard/public address. It carries fictional game state, optional user-entered card details and bearer capabilities; use the trusted room LAN or verified private HTTPS path. Never put the relay on a public port.

If the hub drops, people reconnect to their saved progress. Restore the same relay command. Restarting the web app with `./siege restart` preserves progress and pauses active experiences for their owners to resume.

## Five-minute preflight

- `./siege status` must print one healthy experience URL.
- Open the same link on two devices. Start one and confirm the other stays at welcome.
- Complete a challenge and use Reset/Restart on the other device; the first must retain its progress.
- Download a test Account Action Card and open an HP resource link/scan the product QR.
- Check the real phone browser and the exact venue WiFi path. Physical Safari/Android checks remain venue work; desktop viewport emulation does not certify them.
- On a shared laptop, press Reset before the next participant. There is no separate sign-in or station setup page.
