# Single-experience architecture

One FastAPI/Uvicorn process on 127.0.0.1:8090 owns the current experience. Every person opens `/`; the city, choices, robot bubbles, lesson cards and Account Action Card are stages of one responsive page. Previous role paths and the old HTML playbook selector redirect to `/`.

```
Each browser opens the same private root URL
    -> anonymous browser nonce -> its own persisted personal game + bearer capability
    -> WebSocket actions/state for that personal game
    -> deterministic scoring + self-paced phase control
    -> common bounded local AI analysis pool -> unchanged Nemotron :8000
    -> authenticated debrief/card data -> local WeasyPrint PDF
```

## Independent progress and reset

The SQLite `experiences` table maps a random browser nonce to a one-team game room and capability. Repeated bootstrap returns the same progress. Different browsers have different rooms; multiple tabs in one browser resume the same experience. The nonce and bearer never enter a public URL.

Personal control endpoints resolve the capability to its owning room, with no caller-supplied room override. Reset clears only that person’s score, choices, card data and analysis display, returning to welcome. Restart clears the same state and begins a briefing in the current industry. Both controls are always visible and confirm before clearing. Shared model work and everyone else’s state continue.

Briefing and lesson stages wait for the person to Continue. Challenge timers still decide the game’s downtime/fast-response effects. Pause affects only the owner. A process restart restores progress and pauses active games so their owners can resume. SQLite WAL stores snapshots; use one Uvicorn worker.

The rules are unchanged: combine invoice analysis with human verification; scan all six inbox buildings with SCOUT; deploy SCOUT, SHERLOCK, SHIELD, PATCH, SCRIBE in recovery order. The model never decides scores. SHIELD stops new records exposure; PATCH stops further downtime loss; SCRIBE completes communication. Values are fictional game values.

## Shared local analysis, private decisions

Identical fictional evidence + role + greeting/analysis mode can coalesce into one live model stream. A completed result may be reused for eight seconds, labeled as shared analysis. There is no merging of player choices, score, progress or account details. A detached work object means the first subscriber resetting cannot cancel the result for others.

The existing model endpoint, model ID, container and serving settings are unchanged. The application keeps eight model requests in flight at most. Queue, connection and generation have the existing 7.6-second deadline with short logged fallback guidance. Outputs are escaped and at most 25 words. Actual request/token/evidence counters are counted once for a shared request; the UI’s small common AI panel uses those aggregate observations rather than inventing per-person duplicate work.

Only shipped fictional evidence enters inference. Real account names, card fields and approved optional stories never enter requests or the reuse key. Request hooks block nonloopback AI targets and count actual HTTP request-body exchanges. This remains an application counter, not a whole-host packet capture. The unchanged model stack has previously downloaded runtime artifacts.

## Account Action Card

`revamp/action_card.py` renders a one-page A4 PDF with the original owner-supplied HP mark, result tiles, industry hypothesis, discovery questions, optional account/next-step text and three verified HP resources/QR. The optional fields appear only in an authenticated debrief/card response; public room snapshots omit them. They are not account research or generated account claims.

The local WeasyPrint fetcher allows only the exact generated HP-logo and QR data URIs; no remote asset loading. Two rendering slots bound PDF CPU work. Long fields/optional approved story use a compact layout. The PDF’s resource links deliberately open official HP pages only when the reader chooses them. Metadata is in config/hp_resources.json.

## Private access and compatibility

SSH forwarding, separately verified private Serve or the fixed-upstream room hub all carry the same root page. Share experience copies/encodes the browser-visible private root with no session credentials. The app and relay do not change networking or expose a public port.

The original :8080 application, existing public mapping and both model containers are untouched. Historical shared room data/administrative APIs and legacy PDF exports remain for local compatibility; they do not introduce another human-facing entry page. Historical architecture is in SHARED_ARCHITECTURE.md. The old source/backup/performance reports are preserved; this work does not assert that the earlier 60fps active-wave gate passed.

CSP, bounded WebSocket queues/message sizes, origin checks, per-owner control limits and login/join limits remain. All model/name/card text is escaped. Runtime state, credentials, optional stories, exports and videos stay out of source packages.

## Current guided role orchestration

`revamp/story.py` defines the new presentation/runbook states. New personal sessions have `guided=true`, with a blocked customer-policy illustration before Deploy. One authorized Deploy starts five live local analysis roles. The room ticker advances each simulated action only after that role has a completed result or bounded fallback, then records city-only changes and in-app human-review tasks. No real patch or outside notification is executed.

Story phases, steps, elapsed time, pending reviews and score are persisted per owner. Old in-progress saves remain in the prior mode until their owner restarts. Background guided snapshots batch in a single transaction, while direct owner controls still commit immediately; dirty entries refer to current room objects to prevent stale-tick overwrite. Sources, scope and visual/AI distinctions are documented in GUIDED_STORY.md.
