# Cyber Siege: one link, your experience

## Install on a fresh Fury

```bash
git clone https://github.com/Navigatedhustle/cyber-siege.git
cd cyber-siege
./launch.sh
```

Use Ubuntu 24.04 ARM64 on the tested HP ZGX Fury / GB300, working Docker/GPU
access, Python 3.12, the PDF system libraries and at least 400 GiB initial free
disk. First launch installs the locked app dependencies, downloads the two pinned
model revisions and immutable serving images, waits for both models, and starts
the latest guided experience. Open **http://127.0.0.1:8090/** on the Fury.
Initial download and cold compilation need internet access and can take a long time.

The [comprehensive fresh Fury guide](docs/FRESH_FURY_GUIDE.md) and
[PDF guide](docs/FRESH_FURY_GUIDE.pdf) include prerequisites, exact commands,
private remote access, Zscaler/PAC troubleshooting, walkthrough and teardown.
Use `./launch.sh status` and `./launch.sh stop` for the whole Cyber Siege stack.
Use `./siege` below when you want to control only the web app, keeping models resident.

The GitHub release includes source ZIP/tar, checksums, the PDF and an optional
recorded fallback video. The source policy is `config/distribution-files.json`.
Weights/images are downloaded separately from their publishers; private runtime
data and credentials are excluded. See [asset notices](NOTICE.md).

## Existing private installation

The prior installation used **https://hp-zgx-fury-showcase.taild25e44.ts.net:8443/**
with Tailscale connected. A fresh Fury has its own hostname and private mapping;
follow the guide rather than copying that machine's address. Local SSH-forward
access uses **http://127.0.0.1:8090/**.

Everyone uses the same page. Each browser gets its own city, guided story, pace and Account Action Card. No role selection, room code, nickname, team setup or presenter login is needed. The old role URLs redirect to this page.

```bash
cd ~/cyber_siege
./siege start
./siege status
```

Press **Start the story**, see the attack, then watch a scripted cloud request check and the **DENIED · Scenario policy** outcome. The fictional evidence preview stays local. Press **Deploy local AI squad** to start five local analysis roles and an automatic city-only response plan. The local evidence console, findings and completed action results make the scan, issue identification and recovery visible. Seller value cards explain the approved data boundary, dedicated capacity planning, scoped actions and human approval while the robots move. Each lesson waits for you to continue. Another person’s progress never moves yours.

Cloud models can support authorized defense. The cloud tile is a scripted customer-policy illustration with no cloud API call; live local analysis, fictional recovery actions and in-app human-review tasks are labeled separately. See [the guided story and sources](docs/GUIDED_STORY.md).

- **Reset** clears your results/card details and returns you to the welcome screen.
- **Restart** clears your results/card details and begins the same industry again.
- Both controls are always in the header, ask before clearing, and affect only your experience.
- **Share experience** copies or shows a QR for the same entry link for other people on the private connection.

At the end, optionally add an account/opportunity and your next step, then download the one-page **Account Action Card**. It includes 12 sourced HP ZGX Fury / GB300 capabilities paired with customer benefits, including rackability, ZTK, Z Runtime and RHEL hardware certification. Discovery questions, results, personalization, official HP/Red Hat links and the HP product QR remain on one A4 page. Account details stay out of the fictional city and never enter a model prompt.

To stop or restart only the managed web application:

```bash
./siege stop
./siege restart
```

None of these commands changes model servers, drivers or networking. The original individual application on :8080 and its existing public mapping remain untouched. Do not use that mapping for this private revamp.

[How the single experience works](docs/SINGLE_EXPERIENCE.md) · [Private room access](docs/ROOM_SETUP.md) · [Architecture](docs/ARCHITECTURE.md)

## Validation

```bash
.venv/bin/python -m pytest -q
.venv/bin/python scripts/revamp/guided_browser.py
.venv/bin/python scripts/revamp/guided_load.py
.venv/bin/python scripts/revamp/action_card_check.py
```

The current proof files are `docs/guided-story-browser.json`, `docs/guided-story-load.json` and `docs/single-experience-card.json`. The guided load script drives 60 independent browser-token sessions through all three incidents with three Deploy clicks each and real local inference. Identical fictional evidence requests can share the same current model analysis for eight seconds; choices, scores and account details remain independent. Actual model/evidence/token counters are counted once.

Fictional Northwind and all game amounts are explicitly labeled. Fury is a platform for local AI assistance, not a security product. The prior four-role interface, old acceptance reports and backup recording are historical artifacts; the earlier active-wave 60 fps target was not certified and is not represented as a passing result for this new page. Reduced intensity is the default.

Private stories, passwords, runtime databases, exports, models and video are not packaged. The working ledger is `~/siege/STATE.md`; the original `siege_v1_snapshot` tag is retained.
