"""Broker gateway exception hierarchy."""

from __future__ import annotations


class BrokerError(Exception):
    """Base class for any broker-gateway error."""


class NotConnectedError(BrokerError):
    """Raised when an operation requires an open broker session and none exists."""


class NonPaperAccountError(BrokerError):
    """Raised when the connected account is not in the paper-account allowlist.

    The broker gateway is fail-closed: if we cannot positively identify the
    account as a paper / demo account (or `dry_run=True`), every order-placing
    method must refuse to operate.
    """


class OrderRejectedError(BrokerError):
    """Raised when the broker rejects an order outright."""


__all__ = [
    "BrokerError",
    "NonPaperAccountError",
    "NotConnectedError",
    "OrderRejectedError",
]
