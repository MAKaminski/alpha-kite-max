"""
Pydantic models for trading system.
"""

from datetime import datetime, date
from typing import Optional
from decimal import Decimal
from pydantic import BaseModel, Field


class Position(BaseModel):
    """Position model for tracking open options positions."""
    
    id: Optional[str] = None
    ticker: str = Field(..., description="Stock ticker symbol")
    option_symbol: str = Field(..., description="Option symbol (e.g., AAPL241220C00150000)")
    option_type: str = Field(..., description="PUT or CALL")
    strike_price: Decimal = Field(..., description="Strike price")
    expiration_date: date = Field(..., description="Option expiration date")
    action: str = Field(..., description="SELL_TO_OPEN or BUY_TO_CLOSE")
    contracts: int = Field(default=25, description="Number of contracts")
    entry_price: Decimal = Field(..., description="Entry price per contract")
    entry_credit: Decimal = Field(..., description="Total credit received")
    current_price: Optional[Decimal] = None
    unrealized_pnl: Optional[Decimal] = None
    status: str = Field(default="OPEN", description="OPEN, CLOSED, or EXPIRED")
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    closed_at: Optional[datetime] = None


class Trade(BaseModel):
    """Trade model for recording individual trades."""
    
    id: Optional[str] = None
    position_id: Optional[str] = None
    ticker: str = Field(..., description="Stock ticker symbol")
    option_symbol: str = Field(..., description="Option symbol")
    option_type: str = Field(..., description="PUT or CALL")
    strike_price: Decimal = Field(..., description="Strike price")
    expiration_date: date = Field(..., description="Option expiration date")
    action: str = Field(..., description="SELL_TO_OPEN or BUY_TO_CLOSE")
    contracts: int = Field(..., description="Number of contracts")
    price: Decimal = Field(..., description="Trade price per contract")
    credit_debit: Decimal = Field(..., description="Total credit/debit (positive for credit)")
    trade_timestamp: datetime = Field(..., description="When the trade was executed")
    signal_timestamp: datetime = Field(..., description="When the signal occurred")
    created_at: Optional[datetime] = None


class TradingSignal(BaseModel):
    """Trading signal model."""
    
    id: Optional[str] = None
    ticker: str = Field(..., description="Stock ticker symbol")
    signal_timestamp: datetime = Field(..., description="When the signal occurred")
    signal_type: str = Field(..., description="PUT_SELL, CALL_SELL, or CLOSE_POSITION")
    current_price: Decimal = Field(..., description="Stock price at signal")
    sma9_value: Decimal = Field(..., description="SMA9 value at signal")
    vwap_value: Decimal = Field(..., description="VWAP value at signal")
    direction: str = Field(..., description="up or down")
    action_taken: bool = Field(default=False, description="Whether action was taken")
    position_id: Optional[str] = None
    created_at: Optional[datetime] = None


class DailyPnL(BaseModel):
    """Daily P&L model."""
    
    id: Optional[str] = None
    ticker: str = Field(..., description="Stock ticker symbol")
    trade_date: date = Field(..., description="Trading date")
    total_trades: int = Field(default=0, description="Total number of trades")
    winning_trades: int = Field(default=0, description="Number of winning trades")
    losing_trades: int = Field(default=0, description="Number of losing trades")
    total_realized_pnl: Decimal = Field(default=0, description="Total realized P&L")
    total_unrealized_pnl: Decimal = Field(default=0, description="Total unrealized P&L")
    total_credits_received: Decimal = Field(default=0, description="Total credits received")
    max_drawdown: Decimal = Field(default=0, description="Maximum drawdown")
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class PositionSummary(BaseModel):
    """Position summary for dashboard display."""
    
    ticker: str
    total_positions: int
    open_positions: int
    closed_positions: int
    total_unrealized_pnl: Decimal
    total_realized_pnl: Decimal
    positions: list[Position]


class TradingSummary(BaseModel):
    """Trading summary for dashboard display."""
    
    ticker: str
    date: date
    daily_pnl: Optional[DailyPnL]
    position_summary: PositionSummary
    recent_trades: list[Trade]
    recent_signals: list[TradingSignal]
