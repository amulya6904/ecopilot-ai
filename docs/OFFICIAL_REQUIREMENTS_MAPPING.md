# Official Requirements Mapping

Statuses are deliberately conservative. “Development-only” means the lightweight
harness exercises the concept but cannot satisfy official EnergyPlus evidence.

| Official requirement | Current status | Existing support | Remaining work | Planned phase |
|---|---|---|---|---|
| EnergyPlus simulation | Implemented | Verified 26.1 batch runner, raw outputs and metadata | Runtime callbacks remain Phase 8 | 4–5 |
| IDF building model | Implemented for Phase 5 | Preserved base, Phase 4 telemetry IDF, derived fixed baseline IDF | Future agent input must reuse frozen identity | 4–5 |
| EPW weather file | Implemented | Configured Bengaluru EPW and readiness validation | Preserve matched weather in later comparisons | 4 |
| EnergyPlus Python wrapper | Implemented for batch execution | Explicit subprocess backend with no fallback | Runtime callbacks remain Phase 8 | 4, 8 |
| Telemetry streaming | Partially implemented | Backend-neutral interval schema; lightweight stepping | Stream EnergyPlus callbacks | 4 |
| Zone temperatures | Implemented | Hourly Zone Mean Air Temperature | Fixed baseline comparison remains Phase 5 | 4 |
| Energy consumption | Implemented | Hourly Electricity:Facility, J-to-kWh | Savings comparison remains Phase 10 | 4 |
| Occupancy | Implemented for baseline | Real hourly Zone People Occupant Count; frozen People schedule inventory | Reuse unchanged in agent run | 5 |
| Indoor air quality | Development-only | Lightweight CO2 | Configure supported EnergyPlus IAQ outputs | 4 |
| PMV | Explicitly unavailable | Output requested; retained People objects do not enable Fanger PMV/PPD; nulls preserved | Future model change would require a new frozen baseline | 5 |
| Peak demand | Implemented | Direct hourly facility demand, W-to-kW, official baseline KPI | Compare only after matched agent run | 4–5 |
| Open-source LLM | Not implemented | Disabled agent settings and package boundary | Connect and evaluate Qwen/Mistral/Llama | 7 |
| MCP server | Not implemented | Empty package boundary | Implement bounded tools | 6 |
| Tool calling | Not implemented | Disabled configuration flag | Define schemas and dispatch | 6–7 |
| Runtime error extraction | Implemented | Warning/severe/fatal parser and metadata | Future LLM summaries remain out of scope | 4 |
| Simulation log parsing | Implemented | Raw error preservation and warning classification | None for Phase 4 | 4 |
| Structured control actions | Partially implemented | Shared `ControlAction` schema | Define agent response contract and validators | 6–9 |
| Forward injection | Not implemented | Backend method boundary only | Map validated actions to actuators | 8 |
| Closed-loop operation | Not implemented | Stepwise lightweight harness | Coordinate EnergyPlus→agent→EnergyPlus loop | 8 |
| Official EnergyPlus baseline | Implemented | Frozen hashes, fixed thermostat policy, official artifacts and repeatability proof | Reuse exact inputs for future agent run | 5 |
| Facility energy benchmark | Implemented | Hourly facility electricity converted once from joules | Future matched comparison | 5 |
| Comfort benchmark | Implemented | Occupied conditioned-zone temperature compliance; plenum excluded | PMV unavailable in retained model | 5 |
| Baseline comparison | Partially implemented | Official reference case exists; no agent case or savings result | Run matched agent scenario | 10 |
| kWh savings percentage | Not implemented | No savings claims | Calculate from matched official runs | 10 |
| Comfort-preservation proof | Not implemented | Temperature/CO2 development metrics | Prove PMV/constraints on official runs | 9–10 |
| GitHub source code | Partially implemented | Local source repository | Publish final reviewed source | 12 |
| Architecture document | Implemented | `docs/SYSTEM_ARCHITECTURE.md` | Maintain as implementation evolves | 4–12 |
| Presentation | Not implemented | Assets directory boundary | Create final deck | 12 |
| Three-minute video | Not implemented | None | Record and edit demonstration | 12 |

Neither a placeholder nor a directory scaffold is evidence that the corresponding
runtime capability works.

Phase 5 establishes the official fixed-schedule EnergyPlus baseline using the
existing verified EnergyPlus example model. Original EnergyPlus zone identifiers
are preserved, while display aliases are used for presentation. This phase does
not implement MCP, an open-source LLM, actuator injection, autonomous control,
optimization, or savings comparison.
