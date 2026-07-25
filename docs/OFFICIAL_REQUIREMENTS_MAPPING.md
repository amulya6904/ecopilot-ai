# Official Requirements Mapping

Statuses are deliberately conservative. “Development-only” means the lightweight
harness exercises the concept but cannot satisfy official EnergyPlus evidence.

| Official requirement | Current status | Existing support | Remaining work | Planned phase |
|---|---|---|---|---|
| EnergyPlus simulation | Not implemented | Unavailable backend placeholder | Connect executable and runtime/API | 4 |
| IDF building model | Not implemented | Model directory scaffold | Select/create baseline IDF | 4 |
| EPW weather file | Not implemented | Weather directory scaffold | Add licensed/open EPW and validation | 4 |
| EnergyPlus Python wrapper | Not implemented | Backend contract and legacy adapter boundary | Implement runtime/API wrapper | 4 |
| Telemetry streaming | Partially implemented | Backend-neutral interval schema; lightweight stepping | Stream EnergyPlus callbacks | 4 |
| Zone temperatures | Development-only | Three-zone lightweight telemetry | Map EnergyPlus output variables | 4 |
| Energy consumption | Development-only | Lightweight power and interval kWh | Map facility electricity meters | 4–5 |
| Occupancy | Development-only | Seeded zone schedules | Map EnergyPlus occupancy variables | 4 |
| Indoor air quality | Development-only | Lightweight CO2 | Configure supported EnergyPlus IAQ outputs | 4 |
| PMV | Not implemented | Optional schema field and PMV settings | Configure and map EnergyPlus comfort output | 4–5 |
| Peak demand | Development-only | Derived lightweight facility HVAC demand and thresholds | Use EnergyPlus facility demand | 4–5 |
| Open-source LLM | Not implemented | Disabled agent settings and package boundary | Connect and evaluate Qwen/Mistral/Llama | 7 |
| MCP server | Not implemented | Empty package boundary | Implement bounded tools | 6 |
| Tool calling | Not implemented | Disabled configuration flag | Define schemas and dispatch | 6–7 |
| Runtime error extraction | Partially implemented | Shared runtime-error schema; lightweight capture | Parse EnergyPlus severe/fatal errors | 4–6 |
| Simulation log parsing | Not implemented | Log directory and architecture plan | Extract errors and summarize warnings | 4–6 |
| Structured control actions | Partially implemented | Shared `ControlAction` schema | Define agent response contract and validators | 6–9 |
| Forward injection | Not implemented | Backend method boundary only | Map validated actions to actuators | 8 |
| Closed-loop operation | Not implemented | Stepwise lightweight harness | Coordinate EnergyPlus→agent→EnergyPlus loop | 8 |
| Baseline comparison | Development-only | Fixed lightweight benchmark | Run matched EnergyPlus scenarios | 5, 10 |
| kWh savings percentage | Not implemented | No savings claims | Calculate from matched official runs | 10 |
| Comfort-preservation proof | Not implemented | Temperature/CO2 development metrics | Prove PMV/constraints on official runs | 9–10 |
| GitHub source code | Partially implemented | Local source repository | Publish final reviewed source | 12 |
| Architecture document | Implemented | `docs/SYSTEM_ARCHITECTURE.md` | Maintain as implementation evolves | 4–12 |
| Presentation | Not implemented | Assets directory boundary | Create final deck | 12 |
| Three-minute video | Not implemented | None | Record and edit demonstration | 12 |

Neither a placeholder nor a directory scaffold is evidence that the corresponding
runtime capability works.
