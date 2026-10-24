"""Alternative configuration loading and pydantic validation."""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from config_loader import list_alternatives, load_all_alternatives, load_alternative

__all__ = [
    "list_alternatives",
    "load_alternative",
    "load_all_alternatives",
    "validate_alternative",
    "AlternativeConfig",
]


class SensorConfig(BaseModel):
    model_config = ConfigDict(extra="allow")

    camera_height_m: float = 0.3
    sees_full_bush: bool = False
    base_sensitivity: float = 1.0


class ScheduleConfig(BaseModel):
    model_config = ConfigDict(extra="allow")

    every_n_days: int = 3
    only_spray_days: bool = False
    start_hour: float | None = None


class RiskTriggerConfig(BaseModel):
    model_config = ConfigDict(extra="allow")

    enabled: bool = False
    level: Literal["bed", "block"] = "bed"
    action: Literal["none", "human_review"] = "none"
    risk_threshold: float = 0.55


class MobilityConfig(BaseModel):
    model_config = ConfigDict(extra="allow")

    width_m: float = 0.36
    height_m: float = 0.42
    rigid: bool = False
    hours_per_ha: float | None = None
    speed_mps: float = 0.5
    battery_h: float = 1.5
    fail_prob_per_bed: float = 0.0
    mud_slowdown: float = 1.0
    stuck_prob: float = 0.0


class HumanReviewConfig(BaseModel):
    model_config = ConfigDict(extra="allow")

    enabled: bool = False
    sensitivity_small: float = 0.0
    sensitivity_underside: float = 0.0
    review_delay_days: float = 0.0
    review_on_schedule: bool = False


class AlternativeConfig(BaseModel):
    """Validated alternative YAML — engine reads these fields only."""

    model_config = ConfigDict(extra="allow")

    code: str
    name: str = ""
    title: str = ""
    sensor: SensorConfig
    schedule: ScheduleConfig
    mobility: MobilityConfig
    prioritize_by_risk: bool = False
    risk_trigger: RiskTriggerConfig = Field(default_factory=RiskTriggerConfig)
    fog_sensitivity_penalty: float = 1.0
    human_review: HumanReviewConfig = Field(default_factory=HumanReviewConfig)
    mast: bool = False
    platform: Literal["quadruped", "humanoid", "wheeled", "sprayer", "human", "none"] = (
        "quadruped"
    )


def validate_alternative(alt: dict[str, Any]) -> dict[str, Any]:
    """Validate and normalize an alternative dict; return plain dict for the engine."""
    model = AlternativeConfig.model_validate(alt)
    return model.model_dump()
