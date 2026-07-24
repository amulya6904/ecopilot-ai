# EcoPilot AI — Frozen Project Scope

## Goal and objectives

The project goal is a safe smart-building platform that reduces avoidable HVAC
energy use and carbon impact while maintaining comfort and indoor air quality. Its
primary objective is to compare an optimized controller fairly against a fixed
baseline across a repeatable three-zone simulation.

Technical objectives are deterministic simulation, forecasting, candidate-action
evaluation, safety validation, closed-loop execution, explainability, auditability,
and modular external integrations. Business objectives are a credible hackathon
demonstration, transparent savings comparisons, improved operator understanding,
and an extensible route from prototype to building integration.

## Scope

In scope for the future system are three-zone simulation, occupancy, temperature,
humidity and CO2 behavior, HVAC energy calculation, a fixed baseline, deterministic
optimization, a safety supervisor, closed-loop operation, dashboard comparisons,
decision explanations, manual override, and audit history. Differentiators include
carbon-aware optimization, predictive pre-cooling, MCP tools, a local LLM operator
assistant, unsafe-action rejection, and an EnergyPlus adapter.

The zones are:

1. Open Office (`office`)
2. Conference Room (`conference`)
3. Computer Lab (`lab`)

Main future inputs are indoor and outdoor temperature, occupancy, humidity, CO2,
current setpoint, fan speed, ventilation, electricity price, grid carbon intensity,
and time of day. Main future outputs are recommended setpoint, fan speed and
ventilation; expected energy use and saving; comfort score; carbon reduction;
decision explanation; and safety-validation result.

Out of scope for the initial MVP are physical IoT hardware, cloud deployment, mobile
apps, authentication, reinforcement learning, large multi-floor buildings,
production-grade security, Kafka, Kubernetes, and a complex 3D digital twin.

## Control, safety, and integrations

The baseline controller will use fixed occupied/unoccupied schedules and will not
react intelligently to real occupancy. It exists solely as a fair comparison. The
future optimizer will evaluate configured candidates using the conceptual objective:

```text
total_score = energy_cost + comfort_penalty + co2_penalty
              + carbon_penalty + control_change_penalty
```

Safety is independent and safety-first: constraint checks and operator overrides
take precedence over optimization. **The deterministic optimizer will make future
control decisions. The LLM will provide natural-language interaction and tool
orchestration. The safety supervisor will have final authority over every action.**

MCP will expose bounded tools to the later operator assistant; it will not make
control decisions. The local LLM will explain and orchestrate, not bypass safety.
The custom simulator will be built first. EnergyPlus will later be accessed through
an adapter for zone temperature, outdoor conditions, energy readings, and possibly
HVAC setpoint actuators.

## Phase priority order

1. Custom simulator
2. Baseline controller
3. Prediction
4. Optimization
5. Safety supervisor
6. Closed-loop execution
7. Dashboard
8. Metrics
9. MCP
10. Local LLM
11. EnergyPlus adapter

Only requirement freezing, configuration, structure, environment setup, the initial
Streamlit shell, tests, and documentation are implemented in Phase 1.
