# Account Action Card: HP ZGX Fury / GB300

Verified 2026-11-09. The downloadable card now includes 12 capabilities, each paired with a short explanation of why a customer might care. It remains one A4 page, including results, the optional account/next step, five discovery questions, official links and a product QR.

| Capability | Discovery value |
|---|---|
| NVIDIA GB300, up to 20 PFLOPS FP4, 748 GB coherent memory | Evaluate larger local models and richer context; validate precision and workload fit. |
| Rack-mountable, liquid-cooled design with front-to-back airflow | Put shared AI near the team or in an IT-managed rack. |
| Multiple users and concurrent workloads | Share local compute across teams; validate concurrency. |
| Two-system linking and two 400 Gbps QSFP112 ports | Plan capacity growth with supported software and networking. |
| HP Z Toolkit (ZTK) | Discover/pair devices and prepare open-source development tools through VS Code. |
| HP Z Runtime | Pull, serve and monitor models locally; connect inference to applications. |
| Red Hat Enterprise Linux hardware certification | Give IT a validated enterprise Linux support path, for the listed hardware/OS configuration. |
| Ubuntu 24.04 LTS with NVIDIA drivers, CUDA and container tools | Reduce initial AI environment assembly work. |
| BMC management connectivity | Plan remote administration of shared equipment. |
| 2 or 4 TB NVMe and self-encrypting storage options | Keep models/evidence near compute; configure encryption and keys. |
| On-prem data and capacity control | Plan data placement and capacity, including licenses, energy and operations. |
| Open tools and model repositories | Evolve workflows with appropriate model choices. |

Feature claims and source mappings live in `config/hp_zgx_differentiators.json`. Benefits are seller discovery interpretations, not measured customer outcomes or assertions that these features are exclusive to HP.

Primary sources:

- [HP hardware and deployment specifications](https://www.hp.com/us-en/workstations/ai-stations/zgx-fury-ai-station.html)
- [HP Z Toolkit and Z Runtime](https://www.hp.com/us-en/workstations/ai-stations/zgx-ai-stations-software.html)
- [Red Hat catalog entry 318527](https://catalog.redhat.com/en/hardware/system/detail/318527)
- [HP / Red Hat announcement](https://www.hp.com/us-en/newsroom/press-releases/2026/hp-extends-data-center-ai-architecture-to-the-edge.html)
- [Red Hat hardware certification scope](https://access.redhat.com/support/offerings/hwcert)

The card distinguishes RHEL hardware certification from certification of the game, an AI application or an entire software stack. Confirm exact OS/SKU, subscriptions and support terms in the catalog. HP’s announcement describes the broader Red Hat AI Factory integration as planned; it is not presented as a bundled entitlement. The existing demo model stack and OS were not changed.

The published FP4 peak is not the demo’s measured performance. The footer retains the dedicated 200–240V AC requirement, site/rack/cooling checks, configuration options and ZTK client prerequisites. The card does not promise a particular rack height or kit without verified accessory specifications. HP’s linked QuickSpecs/datasheet endpoints could not be fetched, so no additional facts were inferred from them.

Validation: five existing session/download/privacy tests pass. Standard and maximum account/next-step/approved-story layouts both pass one-page and printable-bounds checks, all 12 titles and scope notes are present in extracted PDF text, and all three HP plus two certification/announcement links are present in actual PDF annotations. Both rendered previews were visually reviewed. Proof: `single-experience-card.json` and `screenshots/guided/account-card-preview.png`.

Production verification also completed a separate personal journey through all three incidents over the real private Tailscale HTTPS endpoint. Its authenticated download is one page and contains all 12 differentiators, the entered account/next step and HP software/Red Hat link annotations. Only that test journey was reset afterward. Proof: `account-card-differentiators-live.json`.

Only the card, its end-screen teaser and source metadata changed. The previous 66-test guided-story suite and 60-person game load remain the last full story checks; no new game behavior or model/network settings changed for this update.
