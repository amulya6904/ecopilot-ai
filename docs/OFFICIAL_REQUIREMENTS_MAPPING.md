# Official requirements mapping

Statuses distinguish verified implementation from future production work.
“Development only” means the lightweight harness is excluded from official
EnergyPlus results.

| Official requirement | Status | Evidence | Scope note |
|---|---|---|---|
| EnergyPlus simulation | Verified | Phase 4 batch and Phases 5/8–10 annual/runtime artifacts | EnergyPlus 26.1 |
| IDF and EPW | Verified | Base, telemetry, baseline IDFs; model/weather hashes | Retained example model |
| EnergyPlus Python API | Verified | Batch runner and Runtime/Data Transfer callbacks | Local installation |
| Zone/facility telemetry | Verified | Hourly zone and facility artifacts | Six zones; one controlled |
| Energy consumption | Verified | `Electricity:Facility` converted J to kWh | Official source meter |
| Component energy | Verified as available | Exact requested meter names and mapping table | HVAC equals fan in retained model; never summed |
| Occupancy | Verified | EnergyPlus People output and frozen schedule fingerprint | Plenum excluded from comfort |
| Indoor air quality | Development only | Lightweight simulator CO₂ | No official IAQ claim |
| PMV/PPD | Unavailable | Null telemetry and explicit unavailable reason | Occupied temperature is proxy |
| Peak demand | Verified | Hourly EnergyPlus facility demand | Final difference essentially unchanged |
| Open-source LLM | Verified advisory | Local Ollama `qwen3:4b` artifacts | No direct actuator authority |
| MCP server/tools | Verified | 16 bounded tools, resources, stdio audit | Read-only by default |
| Structured proposal | Verified | Compact JSON schema, typed validation | Advisory, not applied action |
| Runtime-error/log parsing | Verified | Raw warnings and classified severity artifacts | Zero severe/fatal in accepted runs |
| Forward actuator injection | Verified | `SPACE1-1` cooling-setpoint write and observation | One actuator |
| Closed-loop recovery | Verified | Reset, fallback, rollback, emergency evidence | Deterministic final authority |
| Safety fault injection | Verified | 22/22 scenarios and all six outcomes | Prototype, not certification |
| Official baseline | Verified | Phase 5 annual manifest and telemetry | Fixed schedule |
| Compatible controlled run | Verified | Phase 10 gate and aligned annual telemetry | Deterministic policy |
| kWh / percentage comparison | Verified | 5.626075812324416 kWh / 0.009606022839067856% | Small whole-building effect |
| Comfort comparison | Verified proxy | +0.16718913270637614 percentage points | PMV unavailable |
| Cost/carbon | Derived | INR 8/kWh and 708 g CO₂/kWh assumptions | Not native utility/grid data |
| Reproducibility | Verified | Repeat report linked to displayed comparison ID | Tolerance `1e-6` |
| Quantitative dashboard | Complete | Phase 10 plus Home and evidence pages | Offline, artifact-backed |
| Architecture document | Complete | `docs/SYSTEM_ARCHITECTURE.md` | Submission deliverable |
| Demo script | Complete | `docs/DEMO_SCRIPT.md` | Three-minute maximum |
| Presentation content | Complete | `docs/PRESENTATION_OUTLINE.md` | PPTX/PDF remains a human export |
| Public GitHub/video/upload | Manual | Submission checklist | URL and media not fabricated |

## Phase boundaries

- Phases 1–3 establish configuration and development-only simulation.
- Phases 4–5 establish the official EnergyPlus engine and baseline.
- Phase 6 exposes bounded official evidence through local MCP.
- Phase 7 demonstrates local qwen3:4b advice with typed output and timeouts.
- Phase 8 proves real actuator discovery, injection, observation, and reset.
- Phase 9 retains deterministic safety authority and validates recovery.
- Phase 10 performs compatible, aligned, claim-gated, reproducible comparison.
- Phase 11 presents existing evidence through a professional offline dashboard,
  documentation, demo guidance, tests, and a compact submission index.

No phase relabels development output as official, fabricates PMV, grants the LLM
direct control, or enlarges the measured energy result.

## Remaining production work

Multi-zone coordination, native PMV inputs, formal safety/security
certification, site-calibrated demand and comfort rules, real tariff/carbon
data, physical BMS integration, and a read-only building shadow pilot remain
future work.
