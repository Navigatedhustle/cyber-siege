# One link, independent progress

The only user-facing entry is `/`. The city, business meters, choices, local AI roles, lesson cards and download are stages of that one page. `/screen`, `/play`, `/station`, `/stations` and `/facilitator` redirect to `/`; users do not choose between access screens.

Each browser creates a random anonymous identifier and resumes its own persisted experience. The server issues a bearer capability for that person’s progress, choices and card. There is no account registration. Different devices/independent browser profiles get different experiences; multiple tabs in the same browser deliberately resume the same one. A shared table device should use Reset between people.

## Reset and restart

The header stays visible while scrolling, including on phones. Reset returns to the welcome screen; Restart goes directly to a fresh briefing in the current industry. Both clear that person’s score, choices and card details, with a confirmation that can be cancelled. They cannot target another person’s session. The model, other people’s experiences and shared AI analysis continue.

Briefing and lesson cards advance only when the person chooses Continue. Challenge timers run while the challenge is active; Pause stops that person’s clock. A server restart preserves progress and pauses active sessions, which can be resumed in the same page.

## Account Action Card

The download is available after the three challenges. Account/opportunity (80 characters) and next step (200 characters) are optional. They appear only in the authenticated debrief/card; public state and the fictional city omit them. They never enter the local model request or shared-analysis key.

The PDF uses the existing local WeasyPrint pipeline with the original owner-supplied HP mark. A navy/cyan header, result tiles, two-column conversation plan, five questions, next-step panel and HP resource/QR area fit one A4 page. Long fields or an approved optional story use a compact layout. Remote PDF asset loading is disabled. The QR and links work when the reader chooses to open an official HP website; generation itself is entirely local.

Resources verified on 2026-11-09:

- HP ZGX Fury overview: https://www.hp.com/us-en/workstations/ai-stations/zgx-fury-ai-station.html
- HP ZGX AI software: https://www.hp.com/us-en/workstations/ai-stations/zgx-ai-stations-software.html
- HP Z AI stations comparison: https://www.hp.com/us-en/workstations/ai-stations.html

Metadata is in `config/hp_resources.json`. No hardware performance or independent-security-product claim is added. A discovery hypothesis is labeled as a hypothesis, not account research. `config/stories.local.json` remains private and optional; no approved story is installed by this change.

## Multi-person AI work

People can act independently on the same fictional dataset. Identical role/evidence requests coalesce into one live stream; a completed identical result may be reused for eight seconds. The UI labels reused analysis. The model output has no control over scoring, actions or phase. Requests contain only the shipped fictional evidence.

Shared work is a separate object, so the first person resetting cannot cancel the result for others. Per-person choices, game numbers and card details are never shared or merged. The small local-AI strip displays actual aggregate active calls, evidence submissions and reported token rate, with no duplicate counters for reuse. Failure guidance stays bounded by the existing 7.6-second request deadline.

The 60-person test completes a deliberately simultaneous full journey, checks distinct session ownership and verifies reset isolation. This is a server/protocol stress test, not a claim of physical venue attendance. Chromium desktop/mobile viewports and Firefox were checked; physical phones, venue WiFi and printed-link reachability still require the real private-path preflight.

## Operator commands

`./siege start`, `./siege status`, `./siege restart`, `./siege stop`. Status prints one experience URL. The local legacy administrative API/room data remain for compatibility and maintenance, but do not introduce another user-facing screen. No model/container or host networking changes are performed.

Existing historical source/report changes were preserved before editing in `~/siege/backup/before-single-experience-*.patch`. Prior stopped motion profiling was not resumed. This new flow is validated on its own behavior and defaults to reduced intensity.
