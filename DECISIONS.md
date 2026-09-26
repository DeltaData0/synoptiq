# Decision log

| ID | Date | Decision | Status | Rationale / evidence |
| --- | --- | --- | --- | --- |
| D-001 | 2026-09-26 | Scope the MVP to regional rainfall-bust replay using GEFSv12 and IMD rainfall. | Active | Canonical reference §§3–4. |
| D-002 | 2026-09-26 | Use train/validation/test years 2010–15 / 2016–17 / 2018–19. | Pending data gate | No random row split. |
| D-003 | 2026-09-26 | Keep fixture mode visibly labeled until real source retrieval and window audit pass. | Active | Prevents unsupported model claims. |
| D-004 | 2026-09-26 | Withhold Day 10 until +240/+246-hour accumulation alignment is audited. | Active | Exact 03–03 UTC window is unverified. |

Add a dated entry for any changed source, time convention, split, label policy, feature set, or released model.

## Team roster and ticket ownership — 2026-09-27

| Plan role | Team member | GitHub profile | Accountable scope |
| --- | --- | --- |
| A — data lead | Kanishka Pandey | `@kan9667` | GEFS inventory/download/decoding, accumulation audit, source manifest |
| B — verification lead | Aanya Varshney | `@aanyavarshneyav` | IMD decoding, land regions, area coverage, labels |
| C — ML lead | Rudraksh Saini | `@Rudrakssh` | Baselines, model, calibration, metrics |
| D — features/explainability lead | Dhruv Makkar | `@dhruvsded1` | Issue-time features, analogs, grouped TreeSHAP |
| E — product lead | Aadi Jain | `@DeltaData0` | API, dashboard, offline bundle |
| F — integration/communication lead | Triman Singh Chadha | `@Triman01` | Acceptance gates, smoke, storyboard, slides, submission package |

Ticket ownership follows the named A–F assignments in Plan §§8–9 and the Submission Roadmap in `AGENTS.md`. GitHub invitations use only the supplied usernames; responsibilities from prior projects are not carried into this SIH project.
