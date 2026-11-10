# Cyber Siege: fresh Fury installation and launch guide

Release 1.0.1 | 10 November 2026 | Prepared for HP sellers and technical operators

Source: https://github.com/Navigatedhustle/cyber-siege

Release assets: https://github.com/Navigatedhustle/cyber-siege/releases/tag/v1.0.1

## 1. What you are installing

Cyber Siege is a guided, individual sales demonstration. A fictional Northwind city
faces an invoice scam, phishing emails and a ransomware/data-theft incident. Five
friendly robot roles explain the evidence using real local Nemotron inference.
The city recovery is a deterministic simulation. After three incidents, each
visitor can download a personalized, one-page Account Action Card with 12 sourced
HP ZGX Fury capabilities and customer benefits.

Everyone opens one page and progresses independently. There is no presenter login,
role selector, team code or account signup in the latest guided experience. Older
role URLs redirect to the same page. Multiple tabs in one browser share progress;
independent browser profiles/devices get independent sessions.

The scripted cloud request check illustrates a fictional customer's evidence-upload
policy. DENIED is a local animation, not a call to a cloud provider. Both cloud and
local models can support authorized defense. Local analysis is live; isolation,
patching, recovery and human review tasks affect only the fictional game. HP ZGX
Fury is an AI computing platform, not a security product that stops breaches by itself.

## 2. Before you start

Use the tested Ubuntu 24.04 ARM64 HP ZGX Fury with one NVIDIA GB300. The qualified
GPU reports approximately 256703 MiB HBM. This release does not claim compatibility
with a smaller GPU, a Windows host, an x86 workstation or an arbitrary cloud VM.
The qualified host used NVIDIA driver 595.99.02; have IT confirm that the installed
driver supports the pinned containers before installing on a different Fury.

Reserve at least 400 GiB initial free disk for model weights, serving images,
environments and runtime caches. Both models stay resident in the qualified profile;
the prior measured lineup left only a few GiB HBM free. Stop other GPU workloads
using their own launchers before starting Cyber Siege. Do not run the Fury V3
showcase model stack at the same time.

The operator needs Python 3.12, git, curl, tar, Docker access and an existing working
NVIDIA driver. Docker GPU access must work through the existing NVIDIA runtime or
the bundled per-container ARM64 device/library wrapper. The wrapper changes no
Docker daemon, driver or host network settings. Have IT provision the host first.

The model/container registries and package indexes need to be reachable. The
Infinity server may download FlashInfer attention-kernel artifacts at runtime.
Air-gapped cold installation has not been certified. A package/registry access
denial should be resolved with the account or network owner, using the original
publisher's terms. Do not paste access tokens into the guide or a public issue.

## 3. Host prerequisite checklist

Run these read-only checks on the new Fury:

```bash
uname -m
python3 --version
nvidia-smi
docker info
df -h .
```

Expected: aarch64, Python 3.12, NVIDIA GB300, a working Docker daemon and sufficient
disk. If the login lacks the Docker supplementary group but the account is already
a member, the launch scripts use sg docker. They do not change group membership.

Have the host administrator install the following application prerequisites if
they are missing. These commands are for a newly provisioned Ubuntu 24.04 Fury;
the application itself never runs apt, sudo, driver installation or a reboot.

```bash
sudo apt-get update
sudo apt-get install -y python3.12-venv git curl \
  libpango-1.0-0 libpangoft2-1.0-0 libharfbuzz0b \
  fonts-dejavu-core
```

Docker Engine and the NVIDIA driver/container support are separate host prerequisites.
The app does not replace them. If docker info requires permission, use the host's
approved Docker access procedure, then sign in again if group membership changed.

## 4. Copy, paste and launch from GitHub

On the Fury, copy these lines into a terminal:

```bash
git clone --branch v1.0.1 \
  https://github.com/Navigatedhustle/cyber-siege.git
cd cyber-siege
./launch.sh
```

First launch checks prerequisites, creates the repository-local .venv, installs
requirements.lock, generates fictional evidence, obtains the pinned models and
immutable images, starts the existing model launchers, waits for readiness and
starts the guided app on loopback 8090. The command prints OPEN when ready.

Open this on a browser running on the Fury:

http://127.0.0.1:8090/

Click Start the story. A desktop browser opens automatically only when the Fury
session has a graphical display. An SSH session prints the URL; it cannot open
the browser on your laptop. Use section 7 or 8 for a separate device.

Keep the initial terminal visible. Downloads depend on connection speed; model
loading and first-run kernel compilation may take tens of minutes. Each model
readiness stage has a bounded wait of about 40 minutes. A container ID alone does
not mean the model is ready. If the command fails, read the displayed error and
diagnose the existing process before trying again. Never start a second stack.

## 5. Install from the release ZIP instead

Use a new empty directory. The release includes ZIP, tar.gz and SHA256SUMS.
Download all three named files below into that directory:

```bash
base=https://github.com/Navigatedhustle/cyber-siege
base=$base/releases/download/v1.0.1
curl -fL "$base/cyber-siege-v1.0.1.zip" -O
curl -fL "$base/cyber-siege-v1.0.1.tar.gz" -O
curl -fL "$base/SHA256SUMS" -O
sha256sum --ignore-missing -c SHA256SUMS
python3 -m zipfile -e cyber-siege-v1.0.1.zip .
cd cyber-siege-v1.0.1
sha256sum -c SOURCE_SHA256SUMS
chmod +x launch.sh siege scripts/*.sh
chmod +x scripts/container-bin/docker vendor/infinity/run.sh
./launch.sh
```

Every downloaded archive and every source file must verify. The tar.gz is an
alternative to the ZIP; extract one, not both into the same installation. The
release checksums also cover the PDF and recorded fallback when downloaded.
Weights, containers, personal state and Python environments are intentionally
obtained or created during setup rather than hidden in the source archive.

## 6. What the launcher controls

The guided app binds 127.0.0.1:8090. The qualified model stack uses Nemotron 3 Super
on 127.0.0.1:8000 and GPT OSS 120B on 127.0.0.1:8001. The latest guided experience
uses Nemotron; GPT OSS remains in the retained qualified two-model lineup for
the legacy application and comparison tools. No model is silently substituted.

Nemotron is NVIDIA-Nemotron-3-Super-120B-A12B-NVFP4 at revision:

ff433f5493e25d631c9f12b5d55c674229923d02

GPT OSS is openai/gpt-oss-120b at revision:

b5c939de8f754692c1647ca79fbf85e8c1e70f8a

Immutable serving image digests are recorded in config/model-images.sh. The
HP/Infinity vendor launcher remains the Nemotron container lifecycle owner.
The challenger is started first with a 0.32 GPU memory fraction; Infinity then
uses the qualified remaining-memory configuration. Context, batch and concurrency
settings are retained in scripts/models_up.sh and scripts/start_challenger.sh.

The launcher rejects another installation's model containers and unknown model
port owners. It checks active GPU process ownership before starting models.
Container mount paths and repository labels establish ownership; names alone do not.

Useful commands, run from the installed repository:

```bash
./launch.sh doctor
./launch.sh setup
./launch.sh download
./launch.sh models
./launch.sh status
./launch.sh
```

doctor is read-only. setup installs app dependencies. download obtains pinned
models/images without starting them. models starts/waits for the models. The
default command completes those stages and starts the latest guided web page.
Repeat downloads reuse/resume the model cache, but internet/registry access may
still be required. Model artifacts are readable by the vendor service UID 10001;
that permission change is restricted to public Nemotron artifacts, not private state.

## 7. Open from a laptop with private SSH access

On the Fury, run tailscale status or use your approved private SSH address to
identify the new machine. Its address will differ from the original developer's
machine. Keep the app running on the Fury.

On the laptop, open PowerShell or a terminal. Replace the two values below with
the new Fury's login and reachable private address:

```powershell
$furyLogin = 'YOUR_FURY_LOGIN'
$furyAddress = 'YOUR_FURY_PRIVATE_IP'
ssh -N -o ExitOnForwardFailure=yes `
  -L 8090:127.0.0.1:8090 "$furyLogin@$furyAddress"
```

Keep that terminal open. Open http://127.0.0.1:8090/ on the laptop. The SSH command
creates the local forward; opening the URL alone does not. A PowerShell continuation
uses a backtick; Bash uses a backslash. If you prefer a single line, use:

```bash
ssh -N -L 8090:127.0.0.1:8090 YOUR_LOGIN@YOUR_FURY_PRIVATE_IP
```

This forwarding method does not serve a phone through the laptop's loopback
address. Each laptop needs its own forward, or use the private HTTPS/room hub paths.

## 8. Private Tailscale HTTPS for click-to-open access

Both the Fury and browsing device must be connected to the approved tailnet,
with permission to communicate. Have the network owner configure private Serve
for the new Fury. The app does not change tailnet access rules or enable public
Funnel. Inspect current mappings first so another application's route is preserved:

```bash
tailscale status
tailscale serve status
tailscale serve --bg --https=8443 --yes http://127.0.0.1:8090
tailscale serve status
```

Use the HTTPS8443 hostname printed by Serve, including :8443 and the final slash.
This is the same page for every visitor. Validate the certificate normally.
Keep a bookmark and use Share experience for the entry link or QR. The QR does
not enroll a device into Tailscale or grant network permission.

For private visitors on the tailnet, the full hostname must resolve to the Fury's
Tailscale address on the visitor's machine. A machine that also has a public Funnel
can have a different public DNS answer. Chrome or a proxy using public DNS may
reach the wrong path even when tailscale ping succeeds.

## 9. Zscaler, proxy and Chrome troubleshooting

The original HP laptop incident was diagnosed precisely: Windows DNS resolved the
private Tailscale address and curl with --noproxy reached the app, while Zscaler's
local PAC sent Chrome to the public Funnel route. The server closed private8443
requests arriving through that public route. Restarting Chrome and disabling
custom Secure DNS did not fix the PAC selection.

On the affected Windows laptop, use the actual URL for its new Fury:

```powershell
$u = 'YOUR_FULL_PRIVATE_HTTPS_URL'
Resolve-DnsName ([uri]$u).Host
curl.exe --noproxy '*' -I --connect-timeout 10 $u
$p = [System.Net.WebRequest]::GetSystemWebProxy()
$p.GetProxy([uri]$u).AbsoluteUri
```

An HTTP405 with Allow: GET from Uvicorn means the HEAD diagnostic reached the
application successfully. The page implements GET, not HEAD. A selected proxy
such as 127.0.0.1:9000 is a separate browser routing path from the direct curl.

To inspect how the proxy is configured without changing it:

```powershell
$k = 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Internet Settings'
Get-ItemProperty $k |
  Select-Object ProxyEnable,ProxyServer,ProxyOverride,AutoConfigURL
```

For a manual proxy, its owner can add the exact private demo hostname to the
proxy exception list while preserving existing entries. Manual exceptions do not
override an automatic PAC script. On the original laptop, ProxyEnable was zero,
AutoConfigURL referenced a localproxy PAC and the listener was ZSATunnel.

For an HP IT-managed Zscaler PAC, send IT this scoped change request:

Please route the new Fury's exact private demo hostname DIRECT on the client,
using the effective Zscaler Client Connector PAC for the active forwarding mode.
Required traffic is HTTPS and WebSockets on TCP8443. Windows already resolves
the private address and direct curl reaches the app. Add an exact-host rule before
broader proxy rules; refresh the device's profile and verify Chrome progress.

Inside the existing PAC FindProxyForURL function, the configuration owner adapts:

```javascript
if (host.toLowerCase() === 'YOUR_FURY_FULL_HOSTNAME') {
    return 'DIRECT';
}
```

The effective system/Forwarding Profile PAC layer matters; changing only an SSL
inspection or authentication list does not establish direct browser routing.
After the approved profile refresh, GetProxy should return the destination URL
itself and Chrome should open the page with live Progress saved updates.

Official guidance:
https://help.zscaler.com/zscaler-client-connector/best-practices-using-pac-files-zscaler-client-connector

No Zscaler profile change was available from the original Fury session. The
original managed laptop's Chrome acceptance remains pending HP IT's policy change.

## 10. Phones and a room hub

Ordinary phones need a private room LAN hub if they cannot join the tailnet.
Use a tailnet-connected laptop on an approved dedicated LAN/travel router.
Conference Wi-Fi may block device-to-device communication. Verify it before show day.

On the hub laptop, create the SSH forward from section 7. Use Python 3.12 and a
copy of this release's revamp modules and requirements-relay.txt. In a separate
environment, install the relay requirements, then run:

```bash
python -m pip install -r requirements-relay.txt
python -m revamp.relay --upstream http://127.0.0.1:8090 --check
python -m revamp.relay --upstream http://127.0.0.1:8090 \
  --listen YOUR_HUB_PRIVATE_LAN_IP --port 8095
```

Replace the hub address before running. Open http://YOUR_HUB_PRIVATE_LAN_IP:8095/
from room devices. The relay accepts a fixed private upstream and specific private
bind address; it does not configure Wi-Fi/firewall rules or become a general proxy.
Each browser keeps independent progress. If the hub drops, restore the same link;
people can reconnect to their saved sessions.

## 11. Run the experience

At welcome, choose the industry and click Start the story. Watch the fictional
request preflight and DENIED by scenario policy. Read the fictional evidence
preview, then press Deploy local AI squad once for the incident.

SCOUT spots suspicious activity. SHERLOCK explains it. SHIELD recommends isolating
the problem. PATCH supports the recovery plan. SCRIBE drafts the communication.
The five-step runbook is automatic and scoped to the game city; no real system
is patched and no external notification is sent.

Read the local findings and seller value card, then Continue to the next challenge.
Repeat through all three incidents. The final card page lets you optionally add
an account/opportunity and a next step, then Download my Account Action Card.
Account details stay outside the fictional world and never enter model requests.

Pause stops only that visitor's clock. Reset returns that visitor to welcome;
Restart begins the same industry again. Both ask for confirmation and clear that
person's results/card details. They do not reset other visitors. On a shared laptop,
use Reset between people. A reload resumes the same browser's saved progress.

Use the reduced-motion control when needed. The app respects the operating system's
reduced-motion preference. Physical projection, small phones, Wi-Fi and sound must
be checked at the venue. Desktop mobile emulation does not certify physical devices.

## 12. What the counters and claims mean

All game dollar values are fictional. Scoring depends on deterministic game rules,
not the model's opinion. Speech bubbles are bounded to 25 words with a 7.6-second
total inference/queue deadline; a failed or late response uses a scripted fallback.

The small AI panel shows measured aggregate local model work. Identical fictional
evidence requests can share a live stream and a short eight-second result cache.
Personal choices, progress and account details are never coalesced. Reused work is
labeled. The token rate is reported output tokens divided by call duration, not
a comparative hardware benchmark.

Data sent to the cloud refers to game AI request-body exchanges. It is not a
whole-host egress monitor. Container/package/model startup downloads and operator
browser visits to HP resources are outside that counter. No cloud inference is
part of the guided story. The source links in the Account Action Card qualify
performance, software and certification claims; RHEL hardware certification is
distinguished from planned AI Factory integration.

## 13. Preflight and validation

Before sharing the link, confirm both models and the app:

```bash
./launch.sh status
curl -f http://127.0.0.1:8090/health
curl -f http://127.0.0.1:8000/v1/models
curl -f http://127.0.0.1:8001/v1/models
```

In two independent browser profiles, complete an incident in one and reset the
other. The first must keep its progress. Complete all three incidents, download
the card, inspect it and follow one official resource link. Test the actual private
URL on the exact laptop/phone/network you will use for the event.

Technical regression and browser checks are available locally:

```bash
.venv/bin/python -m pytest -q
export PLAYWRIGHT_BROWSERS_PATH="$PWD/runtime/browsers"
.venv/bin/python -m playwright install chromium firefox
.venv/bin/python scripts/revamp/guided_browser.py
.venv/bin/python scripts/revamp/action_card_check.py
```

The browser harness starts only isolated loopback test processes and uses fictional
data. Model calls are real when run against the live endpoint. An optional protocol
stress test is scripts/revamp/guided_load.py; it creates 60 independent journeys.
Run load work separately from presentation and other GPU inference.

Prior validated story load: 60 visitors, WebSocket RTT p95 88.28 ms, model p95
0.763 s, zero fallbacks over 15 actual coalesced calls. This was an accelerated
server/protocol test, not physical venue attendance or a new fresh-host benchmark.
The prior active-wave 60 fps target was not certified. The release's actual fresh
environment checks and limitations are recorded in docs/RELEASE_VERIFICATION.json.

## 14. Common failures and recovery

If a port is occupied, read status and identify its owner. The launcher deliberately
refuses another installation's listeners or GPU workload. Stop that application
using its own controller. Do not kill a PID based only on a port number.

If a model download is interrupted, rerun ./launch.sh download to resume, then
./launch.sh. Verify disk, publisher access and the exact pinned revision/image.
If Infinity is still starting, inspect status/logs and allow its cold compilation
to finish; restarting repeatedly can discard useful initialization progress.

```bash
./launch.sh status
tail -n 80 runtime/revamp/server.log
bash scripts/models_status.sh
```

For container logs, use the existing Docker access path; the supplied vendor
launcher supports run.sh logs from vendor/infinity after the environment has
been established by scripts/model_common.sh. The challenger is named
cyber-siege-challenger. Do not publish raw runtime logs, account fields or credentials.

If only the web application needs recovery while models are healthy:

```bash
./siege restart
```

Saved sessions persist and active experiences pause for their owners to resume.
If live AI fails, scripted bubbles keep the fictional game moving, but report that
fallback honestly. Inspect runtime/revamp fallback logs before claiming live inference.

If the PDF fails, check the Pango/Harfbuzz system libraries and the local error log.
If the browser cannot connect but direct curl works, use the proxy diagnosis in
section 9. A public URL or an unchecked certificate warning is not a private fix.

## 15. Recorded fallback and offline assets

The release optionally includes Cyber-Siege-recorded-fallback.mp4, an H264
1920x1080 recording of the guided story, about 143.52 seconds long. It is recorded
playback, with silent audio, and predates the latest Account Action Card content.
It does not offer live inference, personal progress or interactive card downloads.

Download it from the release page and open it in a local video player if the venue
network is unavailable. Announce that it is a recording. The source and UI assets
run locally with no runtime CDN for art/fonts; live models and their startup artifacts
must already be available for the interactive experience.

## 16. Stop, switch demos and reclaim resources

Stop the entire Cyber Siege stack using its own installation:

```bash
./launch.sh stop
./launch.sh status
nvidia-smi
```

The stop command verifies model-container ownership, stops the guided app and any
verified legacy app, stops the two model containers through their existing
lifecycles, and confirms they are no longer running. It retains source, weights,
caches and saved progress so a later relaunch can reuse them. It does not stop
unrelated services or alter Tailscale/SSH/firewalls.

To retire a private demo mapping that belongs to this installation:

```bash
tailscale serve --https=8443 off
```

Check ownership/current mappings before doing this on a shared Fury. Source deletion
is not required to free GPU compute. Keep weights if you will run the demo again.
For a permanent retirement, the operator may archive private state, remove only this
installation's stopped containers/caches and then delete its ignored model/runtime
directory. Review actual Docker mounts before removal; never prune the shared daemon
or remove another demo's model directory.

The separate Fury showcase V3.1.0 has its own repository, model weights and controller.
Once Cyber Siege is stopped and GPU/model ports are free, launch that installation
with its own ./launch.sh. Preserve its sandbox, model profile and private access.
Retire any former public mapping to port8080 before assigning that port to the
private-only V3 showcase. One live model stack at a time.

## 17. Files, privacy and backup

The release includes all application source, fictional evidence, six industry skins,
original code-native art, HP mark provenance, screenshots, Python locks, model
download/start/stop scripts, relay, tests, guides and explicit distribution policy.

Private runtime state lives in runtime/; optional real account text remains in the
authenticated card flow. .env, SQLite databases, generated exports, stories.local.json,
model weights and Python environments are ignored and excluded from the source
package. Approved optional customer stories must be installed separately, remain
local and must never be inserted into model prompts or a public release.

Back up private state only to an owner-controlled location with restricted permissions.
Stop the app before an ordinary file backup, or use SQLite's online backup API for
a consistent database snapshot. Do not copy a live database without its WAL handling.
The published source archives carry no operational visitor history or secrets.

## 18. Upgrade, rollback and support handoff

Use a separate directory for each release. Stop the old installation before starting
another. Download and verify the new release, follow its guide and do not copy PID
registries between installations. For rollback, stop the new stack and run the prior
installation through its own launcher. Preserve any private progress you need first.

When requesting support, provide the release version, Linux/architecture, GPU name,
the stage that failed, model IDs and sanitized error text. State whether a proxy/PAC
is present and whether a direct loopback/private curl succeeds. Keep account details,
tokens, private stories and full runtime databases out of the report.

For the Zscaler case, the useful evidence is: system DNS resolves private Tailscale,
direct curl reaches Uvicorn, managed PAC selects a proxy, and public Funnel ingress
rejects private8443. HP IT owns the client PAC correction. No server model change
is required for that routing defect.

## 19. Source and reference links

- Cyber Siege source: https://github.com/Navigatedhustle/cyber-siege
- Release and all downloadable assets: https://github.com/Navigatedhustle/cyber-siege/releases/tag/v1.0.1
- NVIDIA Nemotron model: https://huggingface.co/nvidia/NVIDIA-Nemotron-3-Super-120B-A12B-NVFP4
- OpenAI GPT OSS model: https://huggingface.co/openai/gpt-oss-120b
- Tailscale Serve: https://tailscale.com/docs/features/tailscale-serve
- Windows DNS guidance: https://tailscale.com/docs/reference/dns-in-tailscale
- Zscaler PAC guidance: https://help.zscaler.com/zscaler-client-connector/best-practices-using-pac-files-zscaler-client-connector
- Fury showcase V3.1.0: https://github.com/Navigatedhustle/hp-zgx-fury-showcase/releases/tag/v3.1.0

The PDF is generated locally from this Markdown source. Keep both together for
copy-and-paste commands, accessible text and future updates. Acceptance scope and
historical limits stay with the release; a healthy endpoint alone is not a full
fresh hardware installation certification.
