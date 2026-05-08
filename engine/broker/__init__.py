"""Broker gateways for alpha-kite-v2.

Public surface:
  * `AbstractBroker` — base class implementing the BrokerGateway Protocol shape.
  * `DryRunBroker`   — in-memory simulator; never touches a network.
  * `IBKRPaperBroker` — `ib_insync`-backed gateway, fail-closed paper guard.
  * Errors: `BrokerError`, `NotConnectedError`, `NonPaperAccountError`,
    `OrderRejectedError`.
"""

from __future__ import annotations

from engine.broker.base import AbstractBroker
from engine.broker.dry_run import DryRunBroker
from engine.broker.errors import (
    BrokerError,
    NonPaperAccountError,
    NotConnectedError,
    OrderRejectedError,
)
from engine.broker.ibkr_paper import IBKRPaperBroker

__all__ = [
    "AbstractBroker",
    "BrokerError",
    "DryRunBroker",
    "IBKRPaperBroker",
    "NonPaperAccountError",
    "NotConnectedError",
    "OrderRejectedError",
]
