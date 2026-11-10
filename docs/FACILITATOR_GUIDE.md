# Run the single experience

Start the managed game with `cd ~/cyber_siege` and `./siege start`. Open the one URL printed by `./siege status` using the private connection described in ROOM_SETUP.md.

Share that same link with everyone. Each person presses Start the story, deploys the local squad once per incident and watches the guided response at their own pace. There is no presenter screen, room code or team-selection step. You can guide the discussion while using the same page as the participants.

Suggested introduction:

> Northwind is fictional. You will protect its business through three short challenges. Local AI roles analyze the evidence, while a city simulation shows containment, recovery and a human handoff. Everyone progresses independently. At the end you can download an Account Action Card for a real customer conversation. Fury runs local AI; it is not a security product.

Ask people to reflect on the customer pain, what AI helped explain and how they would describe the value after each challenge. The lesson card waits for their Continue action.

Reset is always in the header and clears only that person’s experience back to the welcome screen. Restart begins the same industry again. Both ask before clearing. On shared table laptops, use Reset between people. One person’s reset never clears another’s results.

At the end, people can optionally name an account/opportunity and add a next step. Download my Account Action Card produces a single-page PDF with official HP links and a product QR. Account details never enter a model prompt or the fictional city.

Use `./siege restart` only when you need to restart the web process itself; `./siege stop` ends the managed game service. Both leave models and the original :8080 app untouched. Private transport and venue device checks are still required. The old P0 backup video is available at `~/siege/backup/session.mp4`; it shows the earlier shared format, not this revised individual flow.

## Explain why local AI

Use the same page, with no additional role screens. The cloud lane is labeled as a fictional customer-policy illustration. Say that authorized cloud AI can support defense, but Northwind has not approved sending this evidence there. Do not claim that all frontier models refuse cybersecurity or local AI removes safeguards.

Ask people to click Deploy and watch the five roles. Point at a live local finding and the actual active/peak call counter. Separate the fast inference from the slower presentation of the fictional response plan. Human-review cards show what a real owner would need to approve; no production patch or external notification is sent by the game. Use the value cards to ask about data boundaries, shared compute, tool scope and approvals.

For an old saved game, refresh the page and use Restart to enter the guided flow. The optional private backup `~/siege/backup/guided-session.mp4` shows the new normal-speed guided story; the older session.mp4 shows the historical shared format. See GUIDED_STORY.md for sources and the full scope.
