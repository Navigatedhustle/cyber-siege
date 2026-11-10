# Team game architecture

`python -m revamp` runs one FastAPI/Uvicorn process on 127.0.0.1:8090. The preserved individual application on :8080 and both existing model containers are independent. The revamp never starts, stops or reconfigures model containers.

```
Phones / fixed stations / projector / password console
    -> private SSH / owner-configured private Serve / fixed room hub
    -> one authoritative revamp process on loopback :8090
        -> SQLite WAL room snapshots under runtime/revamp
        -> bounded WebSocket state queues
        -> local streamed Nemotron at 127.0.0.1:8000/v1
```

One process owns rooms, eight team states, timing and choices. SQLite snapshots preserve choices, scores, nickname moderation and station/player identities. Restarts pause active shows, clear in-flight bubbles, and preserve remaining game time. Reconnect tokens retain team identity for at least 30 seconds; they are retained for the room’s lifetime. Reset clears results while keeping joins and station links; a new room gives each group fresh joins.

The normal show budget is 60 seconds briefing, 180 seconds invoice, 180 seconds emails, 240 seconds boss and 20 seconds discussion per wave: twelve minutes. Early completion moves unused wave time into Translate it discussion. Facilitator Next can shorten the show. `SIEGE_TIME_SCALE` is test-only acceleration and visibly labels rehearsal. Default launch always sets it to 1.

Invoice success requires AI analysis and a trusted human vendor check. Paying loses a fictional $48,000 but permits recovery. Inbox success is six unique SCOUT deployments. Boss success follows SCOUT, SHERLOCK, SHIELD, PATCH, SCRIBE; wrong order gives guidance without a score penalty. Each correct action earns 100 points; actions in the first ten game seconds earn 25 extra. Clock-based downtime increases game revenue risk, reduces trust to a floor of 55, and exposes at most 250 fictional records. No AI result, network response time or model opinion changes scores.

Wave replay restores the beginning-of-wave team checkpoint before repeating, preventing score farming. Autopilot uses the same rule function as people. Teams can finish early; the city recovers at containment, with remaining show time used for seller discussion. Room HQ meters average team results; phone meters show that team’s result. Revenue protected compares risk to ten minutes of full downtime at $12,000/minute. All money is explicitly a game value.

## Local AI and real metrics

The existing models.yaml hero endpoint/model ID is used unchanged. Eight revamp calls can run concurrently. Inference requests use a new loopback-only HTTP client with environment proxies and redirects disabled. One shared analysis per role/wave is intentionally deduplicated across teams; the room sees real shared bubbles, not 64 needless model calls. Five boss roles run concurrently. Speech streams in complete words and is capped at 25 words. Failed, empty, overlong or timed-out calls use a role-specific script and append `fallbacks.jsonl`. Total queue, network and generation deadline is 7.6 seconds. `model_calls.jsonl` records completed call duration and fallback status.

Active and peak model calls come from actual request lifecycle counters. Tokens come only from streamed API completion usage. The token/s tile divides reported completion tokens by total call seconds for calls finished in the last ten seconds; this is not a peak or aggregate hardware benchmark. Evidence counts actual rows submitted for model analysis, including repeated role analysis; they are not unique records or a guarantee of model comprehension. The measured AI payload counter uses HTTP request/response hooks: nonloopback targets are blocked independently of configuration; serialized request bodies are counted only when the real exchange returns response headers. Failed connections do not add attempted bytes. No game AI path permits a remote destination, so cloud payload bytes remain zero. This scope excludes private client traffic, other host processes and model-container artifact downloads. No claim of whole-host zero egress is made.

## Security and private data

Facilitator passwords are created locally on first launch and stored as salted scrypt hashes; the initial password file is mode 0600. Administrative sessions use expiring HTTP-only SameSite cookies, separate from player bearer capabilities. Station URLs are HMAC capabilities tied to room/team, intended only for private table devices. Player capabilities travel in the first WebSocket frame, not query strings. Snapshots never contain credentials. Model text, names and link attributes are escaped. No HTML from the model is inserted. A strict CSP excludes inline scripts, eval, external fonts and external network sources.

HTTP bodies, room/player count, joins, logins, connections, message sizes and per-connection message rates are bounded. Actions validate role, phase, pause, team, order and building. Cross-origin mutations and WebSockets are rejected. Bounded send queues replace stale state rather than grow indefinitely. Clients receive plain errors, never stack traces. Rooms store only nicknames and game state; no contact details or real customer names are requested. `config/stories.local.json` is gitignored and must never be copied into a release archive.

The hub forwards only a fixed private upstream. It binds a specific private interface and cannot be used as a generic forward proxy. It makes no firewall, WiFi or Tailscale changes. Venue isolation can block device traffic; test the exact WiFi and station path before the show.

## Debrief playbooks and sound

The local WeasyPrint pipeline renders one-page team playbooks in two bounded worker slots with an in-memory cache keyed to room, industry, team results, measured counters and optional story revision. Remote PDF resource fetches are disabled. Playbook HTML/PDF routes require debrief. Approved story text is escaped and loaded only from the ignored local file, never supplied to a model. The source archive uses only Git-tracked paths.

Briefing greetings are sequential; all five boss model calls run concurrently. Audio uses Web Audio oscillators only on the big screen, requires an initial projector gesture, respects master/local mute, and uses low gain. No media is downloaded.
