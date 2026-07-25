"""Validated, immutable settings for EcoPilot AI."""

from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Mapping


@dataclass(frozen=True)
class SimulationSettings:
    """Time and reproducibility settings for the future simulator."""
    start_hour: int = 8
    end_hour: int = 20
    step_minutes: int = 5
    random_seed: int = 42
    dashboard_step_seconds: float = 1.0
    prediction_horizon_steps: int = 3

    def __post_init__(self) -> None:
        duration_minutes = (self.end_hour - self.start_hour) * 60
        if not 0 <= self.start_hour <= 23 or not 1 <= self.end_hour <= 24:
            raise ValueError("Simulation hours are outside their valid ranges.")
        if self.end_hour <= self.start_hour:
            raise ValueError("Simulation end must be later than its start.")
        if self.step_minutes <= 0 or duration_minutes % self.step_minutes:
            raise ValueError("Step must be positive and divide the simulation duration.")
        if self.prediction_horizon_steps <= 0:
            raise ValueError("Prediction horizon must be positive.")

    @property
    def total_steps(self) -> int:
        """Return the number of simulation intervals."""
        return (self.end_hour - self.start_hour) * 60 // self.step_minutes


@dataclass(frozen=True)
class ComfortSettings:
    """Occupied, unoccupied, and critical temperature boundaries."""
    occupied_preferred_min_c: float = 23.0
    occupied_preferred_max_c: float = 24.0
    occupied_allowed_min_c: float = 22.0
    occupied_allowed_max_c: float = 25.0
    unoccupied_allowed_min_c: float = 20.0
    unoccupied_allowed_max_c: float = 28.0
    critical_min_temperature_c: float = 20.0
    critical_max_temperature_c: float = 27.0

    def __post_init__(self) -> None:
        ranges = (
            (self.occupied_preferred_min_c, self.occupied_preferred_max_c),
            (self.occupied_allowed_min_c, self.occupied_allowed_max_c),
            (self.unoccupied_allowed_min_c, self.unoccupied_allowed_max_c),
            (self.critical_min_temperature_c, self.critical_max_temperature_c),
        )
        if any(low >= high for low, high in ranges):
            raise ValueError("Every comfort minimum must be below its maximum.")
        if not (self.occupied_allowed_min_c <= self.occupied_preferred_min_c
                and self.occupied_preferred_max_c <= self.occupied_allowed_max_c):
            raise ValueError("Preferred range must be inside the occupied allowed range.")
        if not (self.critical_min_temperature_c <= self.occupied_allowed_min_c
                and self.occupied_allowed_max_c <= self.critical_max_temperature_c):
            raise ValueError("Critical limits conflict with the occupied allowed range.")


@dataclass(frozen=True)
class AirQualitySettings:
    """CO2 thresholds in parts per million."""
    outdoor_co2_ppm: float = 420.0
    normal_co2_max_ppm: float = 800.0
    allowed_co2_max_ppm: float = 1000.0
    warning_co2_max_ppm: float = 1200.0
    critical_co2_max_ppm: float = 1500.0

    def __post_init__(self) -> None:
        values = (self.outdoor_co2_ppm, self.normal_co2_max_ppm,
                  self.allowed_co2_max_ppm, self.warning_co2_max_ppm,
                  self.critical_co2_max_ppm)
        if any(left >= right for left, right in zip(values, values[1:])):
            raise ValueError("Air-quality thresholds must be strictly increasing.")


@dataclass(frozen=True)
class HVACSettings:
    """Equipment limits and future optimizer candidate controls."""
    minimum_setpoint_c: float = 20.0
    maximum_setpoint_c: float = 28.0
    minimum_fan_speed_percent: int = 20
    maximum_fan_speed_percent: int = 100
    maximum_setpoint_change_c: float = 2.0
    maximum_fan_speed_change_percent: int = 30
    setpoint_candidates_c: tuple[float, ...] = (21., 22., 23., 24., 25., 26., 27.)
    fan_speed_candidates_percent: tuple[int, ...] = (30, 50, 70, 90)
    ventilation_candidates: tuple[str, ...] = ("low", "medium", "high")
    ventilation_multipliers: Mapping[str, float] = field(
        default_factory=lambda: MappingProxyType({"low": 0.3, "medium": 0.6, "high": 1.0})
    )

    def __post_init__(self) -> None:
        if self.minimum_setpoint_c >= self.maximum_setpoint_c:
            raise ValueError("Minimum setpoint must be below maximum setpoint.")
        if any(not self.minimum_setpoint_c <= value <= self.maximum_setpoint_c
               for value in self.setpoint_candidates_c):
            raise ValueError("Candidate setpoint is outside HVAC limits.")
        if any(not self.minimum_fan_speed_percent <= value <= self.maximum_fan_speed_percent
               for value in self.fan_speed_candidates_percent):
            raise ValueError("Candidate fan speed is outside HVAC limits.")
        if set(self.ventilation_candidates) != set(self.ventilation_multipliers):
            raise ValueError("Ventilation candidates and multipliers must match.")
        if self.maximum_setpoint_change_c <= 0 or self.maximum_fan_speed_change_percent <= 0:
            raise ValueError("Maximum control changes must be positive.")


@dataclass(frozen=True)
class BaselineSettings:
    """Fixed schedule used only as a future fair comparison reference."""
    occupied_setpoint_c: float = 22.0
    occupied_fan_speed_percent: int = 80
    occupied_ventilation: str = "medium"
    unoccupied_setpoint_c: float = 27.0
    unoccupied_fan_speed_percent: int = 20
    unoccupied_ventilation: str = "low"

    def validate(self, hvac: HVACSettings) -> None:
        """Validate fixed schedule values against equipment constraints."""
        for value in (self.occupied_setpoint_c, self.unoccupied_setpoint_c):
            if not hvac.minimum_setpoint_c <= value <= hvac.maximum_setpoint_c:
                raise ValueError("Baseline setpoint is outside HVAC limits.")
        for value in (self.occupied_fan_speed_percent, self.unoccupied_fan_speed_percent):
            if not hvac.minimum_fan_speed_percent <= value <= hvac.maximum_fan_speed_percent:
                raise ValueError("Baseline fan speed is outside HVAC limits.")
        if ({self.occupied_ventilation, self.unoccupied_ventilation}
                - set(hvac.ventilation_candidates)):
            raise ValueError("Baseline ventilation level is invalid.")


@dataclass(frozen=True)
class OptimizationSettings:
    """Weights and reference values for the future deterministic optimizer.

    Future score: energy cost + comfort penalty + CO2 penalty + carbon penalty
    + control-change penalty. No optimization algorithm exists in Phase 1.
    """
    energy_weight: float = 1.0
    comfort_penalty_weight: float = 25.0
    co2_penalty_weight: float = 30.0
    carbon_weight: float = 0.002
    control_change_penalty_weight: float = 0.5
    low_carbon_intensity_g_per_kwh: float = 250.0
    high_carbon_intensity_g_per_kwh: float = 700.0
    default_electricity_price_per_kwh: float = 8.0
    currency_code: str = "INR"

    def __post_init__(self) -> None:
        numeric_values = (value for name, value in vars(self).items()
                          if name != "currency_code")
        if any(value < 0 for value in numeric_values):
            raise ValueError("Optimization numeric values must be non-negative.")
        if not self.currency_code.strip():
            raise ValueError("Currency code must not be empty.")


@dataclass(frozen=True)
class SimulatorPhysicsSettings:
    """Central coefficients and bounds for the Phase 2 development harness."""

    default_setpoint_c: float = 24.0
    default_fan_speed_percent: int = 50
    default_ventilation_level: str = "medium"
    outdoor_heat_transfer_per_hour: float = 0.12
    occupant_heat_gain_c_per_hour: float = 0.80
    cooling_effect_c_per_hour: float = 5.50
    temperature_noise_std_c: float = 0.03
    humidity_noise_std_percent: float = 0.15
    weather_temperature_noise_std_c: float = 0.20
    weather_humidity_noise_std_percent: float = 0.40
    minimum_temperature_c: float = 15.0
    maximum_temperature_c: float = 40.0
    minimum_humidity_percent: float = 20.0
    maximum_humidity_percent: float = 80.0
    maximum_co2_ppm: float = 3000.0
    low_equipment_heat_gain_c_per_hour: float = 0.25
    medium_equipment_heat_gain_c_per_hour: float = 0.50
    high_equipment_heat_gain_c_per_hour: float = 0.90
    co2_generation_factor: float = 0.35
    low_ventilation_removal_fraction: float = 0.03
    medium_ventilation_removal_fraction: float = 0.08
    high_ventilation_removal_fraction: float = 0.15
    humidity_outdoor_transfer_per_hour: float = 0.08
    humidity_occupant_gain_per_hour: float = 0.60
    humidity_dehumidification_per_hour: float = 1.20
    minimum_hvac_power_fraction: float = 0.0
    maximum_hvac_power_fraction: float = 1.0

    def validate(self, hvac: HVACSettings, air_quality: AirQualitySettings) -> None:
        """Validate physics coefficients against Phase 1 equipment settings."""
        rate_names = (
            "outdoor_heat_transfer_per_hour", "occupant_heat_gain_c_per_hour",
            "cooling_effect_c_per_hour", "temperature_noise_std_c",
            "humidity_noise_std_percent", "weather_temperature_noise_std_c",
            "weather_humidity_noise_std_percent",
            "low_equipment_heat_gain_c_per_hour",
            "medium_equipment_heat_gain_c_per_hour",
            "high_equipment_heat_gain_c_per_hour", "co2_generation_factor",
            "humidity_outdoor_transfer_per_hour",
            "humidity_occupant_gain_per_hour",
            "humidity_dehumidification_per_hour",
        )
        if any(getattr(self, name) < 0 for name in rate_names):
            raise ValueError("Simulator rates and noise values must be non-negative.")
        if self.minimum_temperature_c >= self.maximum_temperature_c:
            raise ValueError("Simulator temperature bounds are invalid.")
        if self.minimum_humidity_percent >= self.maximum_humidity_percent:
            raise ValueError("Simulator humidity bounds are invalid.")
        if not hvac.minimum_setpoint_c <= self.default_setpoint_c <= hvac.maximum_setpoint_c:
            raise ValueError("Default setpoint is outside HVAC limits.")
        if not (hvac.minimum_fan_speed_percent <= self.default_fan_speed_percent
                <= hvac.maximum_fan_speed_percent):
            raise ValueError("Default fan speed is outside HVAC limits.")
        if self.default_ventilation_level not in hvac.ventilation_candidates:
            raise ValueError("Default ventilation level is invalid.")
        removals = (
            self.low_ventilation_removal_fraction,
            self.medium_ventilation_removal_fraction,
            self.high_ventilation_removal_fraction,
        )
        if any(not 0 <= value <= 1 for value in removals):
            raise ValueError("Ventilation removal fractions must be between zero and one.")
        if self.maximum_co2_ppm <= air_quality.outdoor_co2_ppm:
            raise ValueError("Maximum CO2 must exceed outdoor CO2.")
        if not (0 <= self.minimum_hvac_power_fraction
                <= self.maximum_hvac_power_fraction <= 1):
            raise ValueError("HVAC power fractions must be ordered within zero and one.")

    @property
    def ventilation_removal_fractions(self) -> Mapping[str, float]:
        """Return immutable ventilation-to-CO2-removal mappings."""
        return MappingProxyType({
            "low": self.low_ventilation_removal_fraction,
            "medium": self.medium_ventilation_removal_fraction,
            "high": self.high_ventilation_removal_fraction,
        })

    @property
    def equipment_heat_gains(self) -> Mapping[str, float]:
        """Return immutable equipment heat gains by configured level."""
        return MappingProxyType({
            "low": self.low_equipment_heat_gain_c_per_hour,
            "medium": self.medium_equipment_heat_gain_c_per_hour,
            "high": self.high_equipment_heat_gain_c_per_hour,
        })


@dataclass(frozen=True)
class EnergyPlusSettings:
    """Phase 4 connection settings for the required final simulation engine.

    Paths are intentionally not checked yet so Phases 1-3 remain usable without
    an EnergyPlus installation or building/weather model files.
    """

    enabled: bool = False
    executable_path: str = ""
    idf_path: str = "energyplus/models/baseline.idf"
    epw_path: str = ""
    output_directory: str = "energyplus/output"
    logs_directory: str = "energyplus/logs"
    modified_models_directory: str = "energyplus/models/modified"
    control_interval_minutes: int = 15
    timeout_seconds: int = 180
    primary_backend: str = "energyplus"
    fallback_backend: str = "lightweight"

    def __post_init__(self) -> None:
        valid_backends = {"energyplus", "lightweight"}
        if self.control_interval_minutes <= 0:
            raise ValueError("EnergyPlus control interval must be positive.")
        if self.timeout_seconds <= 0:
            raise ValueError("EnergyPlus timeout must be positive.")
        if self.primary_backend not in valid_backends:
            raise ValueError("Primary backend must be energyplus or lightweight.")
        if self.fallback_backend not in valid_backends:
            raise ValueError("Fallback backend must be energyplus or lightweight.")


@dataclass(frozen=True)
class AgentSettings:
    """Configuration boundary for a future open-source LLM agent."""

    enabled: bool = False
    provider: str = "ollama"
    model_name: str = "qwen2.5"
    request_timeout_seconds: int = 30
    maximum_retries: int = 2
    maximum_context_records: int = 100
    tool_calling_enabled: bool = False
    mcp_enabled: bool = False

    def __post_init__(self) -> None:
        if not self.provider.strip() or not self.model_name.strip():
            raise ValueError("Agent provider and model name must not be empty.")
        if self.request_timeout_seconds <= 0:
            raise ValueError("Agent request timeout must be positive.")
        if self.maximum_retries < 0:
            raise ValueError("Agent maximum retries must not be negative.")
        if self.maximum_context_records <= 0:
            raise ValueError("Agent context record limit must be positive.")


@dataclass(frozen=True)
class ComfortEvaluationSettings:
    """PMV targets with an explicit temperature fallback for development data."""

    pmv_preferred_min: float = -0.5
    pmv_preferred_max: float = 0.5
    pmv_allowed_min: float = -1.0
    pmv_allowed_max: float = 1.0
    use_temperature_fallback_when_pmv_unavailable: bool = True

    def __post_init__(self) -> None:
        if self.pmv_preferred_min >= self.pmv_preferred_max:
            raise ValueError("Preferred PMV minimum must be below its maximum.")
        if self.pmv_allowed_min >= self.pmv_allowed_max:
            raise ValueError("Allowed PMV minimum must be below its maximum.")
        if not (
            self.pmv_allowed_min <= self.pmv_preferred_min
            and self.pmv_preferred_max <= self.pmv_allowed_max
        ):
            raise ValueError("Preferred PMV range must be inside the allowed range.")


@dataclass(frozen=True)
class PeakDemandSettings:
    """Prototype demand thresholds to calibrate against EnergyPlus in Phase 4."""

    enabled: bool = True
    warning_threshold_kw: float = 24.0
    critical_threshold_kw: float = 30.0

    def __post_init__(self) -> None:
        if self.warning_threshold_kw <= 0:
            raise ValueError("Peak-demand warning threshold must be positive.")
        if self.critical_threshold_kw <= self.warning_threshold_kw:
            raise ValueError(
                "Peak-demand critical threshold must exceed the warning threshold."
            )


SIMULATION = SimulationSettings()
COMFORT = ComfortSettings()
AIR_QUALITY = AirQualitySettings()
HVAC = HVACSettings()
BASELINE = BaselineSettings()
BASELINE.validate(HVAC)
OPTIMIZATION = OptimizationSettings()
SIMULATOR_PHYSICS = SimulatorPhysicsSettings()
SIMULATOR_PHYSICS.validate(HVAC, AIR_QUALITY)
ENERGYPLUS = EnergyPlusSettings()
AGENT = AgentSettings()
COMFORT_EVALUATION = ComfortEvaluationSettings()
PEAK_DEMAND = PeakDemandSettings()
