"""Abstract base for broker gateways.

Concrete brokers extend `AbstractBroker` and implement the BrokerGateway
Protocol declared in `contracts/broker.py`. The abstract base provides:

* a `name` and `dry_run` attribute
* a `_connected` flag and `_assert_connected()` helper
* a `_audit(msg, payload)` hook for downstream integration code
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from typing import Any
from uuid import UUID

from contracts.broker import (
    AccountSummary,
    Fill,
    OrderIntent,
    OrderUpdate,
    Position,
)

from engine.broker.errors import NotConnectedError

logger = logging.getLogger(__name__)


class AbstractBroker(ABC):
    """Skeleton implementation of the BrokerGateway Protocol.

    Subclasses must populate `name` and override the abstract methods.
    """

    name: str = "abstract"

    def __init__(self, dry_run: bool = True) -> None:
        self.dry_run: bool = bool(dry_run)
        self._connected: bool = False

    # ------------------------------------------------------------------
    # Common helpers
    # ------------------------------------------------------------------
    def _assert_connected(self) -> None:
        """Raise NotConnectedError if `connect()` has not been called."""
        if not self._connected:
            raise NotConnectedError(
                f"broker {self.name!r} is not connected; call .connect() first"
            )

    def _audit(self, msg: str, payload: dict[str, Any] | None = None) -> None:
        """Hook for the audit log. Default implementation logs at INFO.

        Real deployments replace this with a writer that persists to the
        Supabase audit table or to JSON Lines on disk.
        """
        logger.info("broker.audit %s payload=%s", msg, payload or {})

    # ------------------------------------------------------------------
    # Abstract surface (matches BrokerGateway Protocol)
    # ------------------------------------------------------------------
    @abstractmethod
    async def connect(self) -> None: ...

    @abstractmethod
    async def disconnect(self) -> None: ...

    @abstractmethod
    async def get_account_summary(self) -> AccountSummary: ...

    @abstractmethod
    async def get_positions(self) -> list[Position]: ...

    @abstractmethod
    async def place_order(self, intent: OrderIntent) -> OrderUpdate: ...

    @abstractmethod
    async def cancel_order(self, intent_id: UUID) -> OrderUpdate: ...

    @abstractmethod
    def stream_order_updates(self) -> AsyncIterator[OrderUpdate]: ...

    @abstractmethod
    def stream_fills(self) -> AsyncIterator[Fill]: ...


__all__ = ["AbstractBroker"]
