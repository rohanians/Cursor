"""
PHASE 2: Live Order Book State Management

Tracks and analyzes real-time order-book data.
Maintains state across multiple updates.
Distinguishes displayed vs. executed liquidity.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from collections import deque
import time


@dataclass(frozen=True)
class OrderBookSnapshot:
    """Immutable snapshot of order book state at a moment in time."""

    timestamp: float
    best_bid: float
    best_ask: float
    mid_price: float
    spread: float
    spread_pct: float

    bid_depth_20: float
    ask_depth_20: float
    imbalance_20: float

    bid_depth_50: float
    ask_depth_50: float
    imbalance_50: float

    bid_depth_100: float
    ask_depth_100: float
    imbalance_100: float

    bid_liquidity: dict[float, float] = field(
        default_factory=dict
    )
    ask_liquidity: dict[float, float] = field(
        default_factory=dict
    )

    valid: bool = True
    stale_ms: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "best_bid": self.best_bid,
            "best_ask": self.best_ask,
            "mid_price": self.mid_price,
            "spread": self.spread,
            "spread_pct": self.spread_pct,
            "bid_depth_20": self.bid_depth_20,
            "ask_depth_20": self.ask_depth_20,
            "imbalance_20": self.imbalance_20,
            "bid_depth_50": self.bid_depth_50,
            "ask_depth_50": self.ask_depth_50,
            "imbalance_50": self.imbalance_50,
            "bid_depth_100": self.bid_depth_100,
            "ask_depth_100": self.ask_depth_100,
            "imbalance_100": self.imbalance_100,
            "valid": self.valid,
            "stale_ms": self.stale_ms,
        }


class OrderBookState:
    """
    Maintains live order-book state machine.

    Tracks:
    - Current bids/asks
    - Depth at multiple levels
    - Imbalance (normalized -1 to +1)
    - Liquidity persistence
    - Book pressure indicators
    """

    def __init__(
        self,
        stale_threshold_ms: float = 5000.0,
        history_size: int = 100,
    ):
        self.stale_threshold_ms = stale_threshold_ms
        self.history_size = history_size

        self.bids: dict[float, float] = {}
        self.asks: dict[float, float] = {}

        self.best_bid: float = 0.0
        self.best_ask: float = 0.0
        self.last_update: float = 0.0

        # Rolling history for persistence analysis
        self.history: deque[OrderBookSnapshot] = deque(
            maxlen=history_size
        )

    def update(
        self,
        bids: dict[float, float],
        asks: dict[float, float],
        timestamp: float | None = None,
    ) -> None:
        """Update order book from exchange data."""

        if timestamp is None:
            timestamp = time.time()

        self.bids = dict(bids)
        self.asks = dict(asks)
        self.last_update = timestamp

        # Clean zero quantities
        self.bids = {
            p: q for p, q in self.bids.items() if q > 0
        }
        self.asks = {
            p: q for p, q in self.asks.items() if q > 0
        }

        # Update best bid/ask
        if self.bids:
            self.best_bid = max(self.bids.keys())
        if self.asks:
            self.best_ask = min(self.asks.keys())

    def snapshot(
        self,
        timestamp: float | None = None,
    ) -> OrderBookSnapshot:
        """Generate immutable snapshot of current state."""

        if timestamp is None:
            timestamp = self.last_update

        stale_ms = int(
            (time.time() - self.last_update) * 1000
        )
        valid = (
            stale_ms < self.stale_threshold_ms
            and self.best_bid > 0
            and self.best_ask > 0
        )

        mid_price = (
            (self.best_bid + self.best_ask) / 2.0
            if self.best_bid > 0 and self.best_ask > 0
            else 0.0
        )

        spread = (
            self.best_ask - self.best_bid
            if self.best_bid > 0 and self.best_ask > 0
            else 0.0
        )

        spread_pct = (
            (spread / mid_price * 100.0)
            if mid_price > 0
            else 0.0
        )

        # Calculate depths at multiple levels
        bid_20, imb_20 = self._calc_depth(
            self.bids, self.asks, 20
        )
        bid_50, imb_50 = self._calc_depth(
            self.bids, self.asks, 50
        )
        bid_100, imb_100 = self._calc_depth(
            self.bids, self.asks, 100
        )

        snapshot = OrderBookSnapshot(
            timestamp=timestamp,
            best_bid=self.best_bid,
            best_ask=self.best_ask,
            mid_price=mid_price,
            spread=spread,
            spread_pct=spread_pct,
            bid_depth_20=bid_20[0],
            ask_depth_20=bid_20[1],
            imbalance_20=imb_20,
            bid_depth_50=bid_50[0],
            ask_depth_50=bid_50[1],
            imbalance_50=imb_50,
            bid_depth_100=bid_100[0],
            ask_depth_100=bid_100[1],
            imbalance_100=imb_100,
            bid_liquidity=dict(
                sorted(
                    self.bids.items(),
                    reverse=True,
                )[:20]
            ),
            ask_liquidity=dict(
                sorted(
                    self.asks.items(),
                )[:20]
            ),
            valid=valid,
            stale_ms=stale_ms,
        )

        self.history.append(snapshot)
        return snapshot

    @staticmethod
    def _calc_depth(
        bids: dict[float, float],
        asks: dict[float, float],
        depth_levels: int,
    ) -> tuple[tuple[float, float], float]:
        """
        Calculate notional depth and imbalance.

        Returns:
            ((bid_depth, ask_depth), imbalance_normalized)
        """

        sorted_bids = sorted(
            bids.items(),
            key=lambda x: x[0],
            reverse=True,
        )[:depth_levels]

        sorted_asks = sorted(
            asks.items(),
            key=lambda x: x[0],
        )[:depth_levels]

        bid_volume = sum(
            price * qty for price, qty in sorted_bids
        )
        ask_volume = sum(
            price * qty for price, qty in sorted_asks
        )

        total = bid_volume + ask_volume

        if total <= 0:
            return (0.0, 0.0), 0.0

        imbalance = (
            (bid_volume - ask_volume) / total
        )

        # Clamp to [-1, 1]
        imbalance = max(-1.0, min(1.0, imbalance))

        return (bid_volume, ask_volume), imbalance

    def imbalance_trend(
        self,
        lookback: int = 5,
    ) -> tuple[float, str]:
        """
        Analyze imbalance persistence over recent history.

        Returns:
            (avg_imbalance, trend_direction)
        """

        if not self.history:
            return 0.0, "UNKNOWN"

        recent = list(self.history)[-lookback:]
        if not recent:
            return 0.0, "UNKNOWN"

        avg_imb = sum(
            s.imbalance_20 for s in recent
        ) / len(recent)

        if avg_imb >= 0.15:
            trend = "BULLISH_PERSISTENT"
        elif avg_imb <= -0.15:
            trend = "BEARISH_PERSISTENT"
        elif avg_imb >= 0.05:
            trend = "BULLISH_WEAK"
        elif avg_imb <= -0.05:
            trend = "BEARISH_WEAK"
        else:
            trend = "NEUTRAL"

        return avg_imb, trend

    def liquidity_disappearance(
        self,
        side: str,
        depth_pct: float = 0.2,
    ) -> bool:
        """
        Detect if liquidity on one side is vanishing.

        Returns True if recent depth < 80% of historical avg.
        """

        if len(self.history) < 5:
            return False

        recent = list(self.history)[-5:]

        if side.upper() == "BID":
            depths = [s.bid_depth_20 for s in recent]
        elif side.upper() == "ASK":
            depths = [s.ask_depth_20 for s in recent]
        else:
            return False

        if not depths or depths[0] == 0:
            return False

        avg = sum(depths) / len(depths)
        current = depths[-1]

        return current < avg * (1.0 - depth_pct)

    def is_stale(self) -> bool:
        """Check if order book data is too old."""
        stale_ms = (time.time() - self.last_update) * 1000
        return stale_ms > self.stale_threshold_ms
