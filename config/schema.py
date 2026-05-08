"""Pydantic models that validate config/strategy.yaml."""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

FeedName = Literal[
    "yfinance",
    "ibkr_delayed",
    "replay",
    "synthetic_options",
    "ibkr_live",
]
OptionsFeedName = Literal["synthetic", "ibkr_live"]
BrokerMode = Literal["paper", "live"]
EntryMode = Literal["directional", "straddle"]


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class DataConfig(_Strict):
    feed: FeedName = "yfinance"
    bar_interval_seconds: int = 60
    options_feed: OptionsFeedName = "synthetic"
    replay_path: str | None = None  # required if feed == replay


class BrokerConfig(_Strict):
    name: Literal["ibkr"] = "ibkr"
    mode: BrokerMode = "paper"
    host: str = "127.0.0.1"
    port: int = 7497
    client_id: int = 17
    dry_run: bool = True
    paper_account_allowlist: list[str] = Field(default_factory=lambda: ["DEMO", "PAPER"])

    @model_validator(mode="after")
    def _enforce_paper_in_v1(self) -> BrokerConfig:
        # Hard rail: live mode is blocked at config-load time in v1.
        if self.mode == "live":
            raise ValueError(
                "broker.mode=live is blocked in alpha-kite-v2 v1; only 'paper' is allowed"
            )
        return self


class UniverseConfig(_Strict):
    symbol: str = "QQQ"


class SignalParams(_Strict):
    sma_period: int = 9
    vwap_session: Literal["regular", "extended"] = "regular"


class SignalConfig(_Strict):
    name: Literal["sma_vwap_cross"] = "sma_vwap_cross"
    params: SignalParams = Field(default_factory=SignalParams)


class EntryConfig(_Strict):
    strategy: Literal["long_vol"] = "long_vol"
    mode: EntryMode = "directional"
    dte: int = 0
    contracts: int = 1
    max_premium_pct_nav: Decimal = Decimal("0.5")


class ExitConfig(_Strict):
    profit_target_pct: Decimal = Decimal("30")
    stop_loss_pct: Decimal = Decimal("25")
    time_stop_minutes_before_close: int = 30


class RiskConfig(_Strict):
    max_open_positions: int = 1
    daily_loss_limit_usd: Decimal = Decimal("50")
    kill_switch_file: str = "./KILL"


class StrategyConfig(_Strict):
    data: DataConfig = Field(default_factory=DataConfig)
    broker: BrokerConfig = Field(default_factory=BrokerConfig)
    universe: UniverseConfig = Field(default_factory=UniverseConfig)
    signal: SignalConfig = Field(default_factory=SignalConfig)
    entry: EntryConfig = Field(default_factory=EntryConfig)
    exit: ExitConfig = Field(default_factory=ExitConfig)
    risk: RiskConfig = Field(default_factory=RiskConfig)

    @field_validator("entry")
    @classmethod
    def _entry_invariants(cls, v: EntryConfig) -> EntryConfig:
        if v.contracts < 1:
            raise ValueError("entry.contracts must be >= 1")
        if v.max_premium_pct_nav <= 0 or v.max_premium_pct_nav > 100:
            raise ValueError("entry.max_premium_pct_nav must be in (0, 100]")
        return v


def load_config(path: str | Path) -> StrategyConfig:
    """Load and validate a strategy YAML file."""
    raw = Path(path).read_text(encoding="utf-8")
    data = yaml.safe_load(raw) or {}
    return StrategyConfig.model_validate(data)
