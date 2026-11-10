# Cyber Siege: Stop the Breach

An individual, self-guided experience for HP Limitless. Each person uses their own phone or computer, investigates a fictional incident with local AI on one HP ZGX Fury, and creates a personal Account Action Card.

## Start

Open **https://hp-zgx-fury-showcase.taild25e44.ts.net/** and press **Start experience**.

No sign-in, password, name, team or room code is required. Choose an alert, launch your investigation, open the new event, make your decision and continue through the reveal at your own pace. Your browser keeps your place. Other participants and presenter controls do not advance your personal steps.

The [room screen](https://hp-zgx-fury-showcase.taild25e44.ts.net/screen) and [presenter controls](https://hp-zgx-fury-showcase.taild25e44.ts.net/facilitator) are optional and also open without sign-in. Presenter controls and bulk downloads are intentionally accessible to anyone with the app link, following the owner's no-sign-in requirement. Individual progress uses an automatically issued browser token; no account is created.

On the Fury, **`make start`** starts the app if needed and prints its links. It reuses an existing app and does not start or change model servers. It prints no access code because none is used.

## First installation and qualification

1. `make setup` creates the Python environment, installs locked dependencies and creates private configuration in .env.
2. Review .env, content/deployment.yaml and all ten draft industry templates. Add Carlos's exact approved story to content/customer_story.md.
3. If needed, `bash scripts/download_models.sh` downloads pinned models and images after disk checks. Keep all model ports on loopback.
4. At least 90 minutes before the event, run `make models-up`. The capped challenger starts first; Infinity starts last through its unmodified vendor launcher.
5. Run `make warmup`, then `.venv/bin/python scripts/model_gate.py`. Confirm the 30 minute health, JSON and scenario gates before live inference. Leave the models running.
6. `make run` serves the app on http://127.0.0.1:8080. Without qualified live models it uses explicitly labeled real rehearsal recordings when available.
7. Inspect existing Funnel mappings, then expose only the app with `tailscale funnel --bg --yes 8080`. Set PUBLIC_BASE_URL, restart only the app and run `bash scripts/check_funnel.sh`.
8. Open the homepage and press Start experience. Each person gets independent progress and decisions. MAX_PARTICIPANTS defaults to 60 active individual experiences; model request concurrency remains separately bounded.
9. Optionally open /screen on the projector. Its QR starts a personal experience immediately. Participant activity pages in groups of 15; it never forces anyone's phase.

The current individual-flow rehearsal completed 45 live investigations and 45 cards with 45 authenticated browser-token SSE connections, no cached investigations and a slowest investigation of 27.20 seconds. This was an accelerated labeled REHEARSAL, not human attendance or a guarantee for an untested count. Configured admission is 60 unfinished individual experiences; 45 concurrent individuals were measured. See [individual mode](docs/INDIVIDUAL_MODE.md) and [load history](docs/LOAD_TEST.md).

`make test` checks deterministic data/scoring, grounding, replay, persistence, model routing and full individual flows against a local protocol stub. Live model and browser checks are recorded separately. All inference remains on the Fury. Rehearsal and replay are visibly labeled and excluded from live completion counts as appropriate.

The real customer story and exports remain gitignored. Scores use the answer key, never a model opinion. Models do not research accounts or write the customer story. Account cards always state: “Opportunity hypothesis to validate in discovery. Not based on research of this account.” No remote is configured and nothing is pushed.

See the [runbook](docs/RUNBOOK.md) for networking, cold start and fallback paths, [architecture](docs/ARCHITECTURE.md) for data and metric boundaries, [model plan](docs/MODEL_PLAN.md) for qualified profiles, and [Carlos checklist](docs/CARLOS_CHECKLIST.md) for remaining content approvals.
