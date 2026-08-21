import asyncio
import json
import time
from dataclasses import dataclass, field
from typing import Any

import websockets


BYBIT_PUBLIC_WS = "wss://stream.bybit.com/v5/public/linear"


@dataclass
class BybitMarketData:
    symbol: str

    price: float | None = None

    bids: list[list[float]] = field(default_factory=list)
    asks: list[list[float]] = field(default_factory=list)

    trades: list[dict[str, Any]] = field(default_factory=list)

    last_update: float = 0.0

    def orderbook_imbalance(self) -> float:
        """
        Simple top-of-book volume imbalance.

        +1 = entirely bid-side
         0 = balanced
        -1 = entirely ask-side
        """

        bid_volume = sum(
            price * quantity
            for price, quantity in self.bids
        )

        ask_volume = sum(
            price * quantity
            for price, quantity in self.asks
        )

        total = bid_volume + ask_volume

        if total <= 0:
            return 0.0

        return (bid_volume - ask_volume) / total


class BybitPublicFeed:

    def __init__(
        self,
        symbol: str = "BTCUSDT",
        orderbook_depth: int = 50,
    ):
        self.symbol = symbol.upper()
        self.orderbook_depth = orderbook_depth

        self.data = BybitMarketData(
            symbol=self.symbol
        )

        self.running = False

    def _subscription_message(self) -> dict[str, Any]:

        return {
            "op": "subscribe",
            "args": [
                f"orderbook.{self.orderbook_depth}.{self.symbol}",
                f"publicTrade.{self.symbol}",
            ],
        }

    def _process_message(
        self,
        message: dict[str, Any],
    ) -> None:

        topic = message.get("topic", "")
        data = message.get("data")

        if not data:
            return

        # ----------------------------------------
        # ORDER BOOK
        # ----------------------------------------

        if topic.startswith("orderbook."):

            bids = data.get("b", [])
            asks = data.get("a", [])

            self.data.bids = [
                [
                    float(price),
                    float(quantity),
                ]
                for price, quantity in bids
            ]

            self.data.asks = [
                [
                    float(price),
                    float(quantity),
                ]
                for price, quantity in asks
            ]

            if self.data.bids:
                self.data.price = self.data.bids[0][0]

        # ----------------------------------------
        # PUBLIC TRADES
        # ----------------------------------------

        elif topic.startswith("publicTrade."):

            trades = data

            for trade in trades:

                price = float(trade["p"])
                quantity = float(trade["v"])

                side = trade["S"]

                self.data.price = price

                self.data.trades.append(
                    {
                        "timestamp": int(
                            trade.get(
                                "T",
                                time.time() * 1000,
                            )
                        ),
                        "price": price,
                        "quantity": quantity,
                        "side": side,
                    }
                )

            # Keep memory bounded.
            self.data.trades = self.data.trades[-500:]

        self.data.last_update = time.time()

    async def run(self) -> None:

        self.running = True

        print(
            f"Connecting to Bybit public WebSocket..."
        )

        print(
            f"Symbol: {self.symbol}"
        )

        print(
            f"Endpoint: {BYBIT_PUBLIC_WS}"
        )

        while self.running:

            try:

                async with websockets.connect(
                    BYBIT_PUBLIC_WS,
                    ping_interval=20,
                    ping_timeout=20,
                ) as websocket:

                    await websocket.send(
                        json.dumps(
                            self._subscription_message()
                        )
                    )

                    print("Connected.")
                    print("Subscribed to:")
                    print(
                        f"  - orderbook.{self.orderbook_depth}.{self.symbol}"
                    )
                    print(
                        f"  - publicTrade.{self.symbol}"
                    )
                    print()
                    print(
                        "Receiving READ-ONLY market data..."
                    )

                    async for raw_message in websocket:

                        message = json.loads(
                            raw_message
                        )

                        self._process_message(
                            message
                        )

                        if self.data.price:

                            print(
                                f"\r"
                                f"{self.symbol} "
                                f"price={self.data.price:.2f} "
                                f"bid={len(self.data.bids)} "
                                f"ask={len(self.data.asks)} "
                                f"trades={len(self.data.trades)} "
                                f"imbalance="
                                f"{self.data.orderbook_imbalance():+.3f}",
                                end="",
                                flush=True,
                            )

            except asyncio.CancelledError:
                raise

            except Exception as exc:

                print()
                print(
                    f"WebSocket error: {exc}"
                )

                print(
                    "Reconnecting in 3 seconds..."
                )

                await asyncio.sleep(3)

    def stop(self) -> None:
        self.running = False


async def main() -> None:

    feed = BybitPublicFeed(
        symbol="BTCUSDT",
        orderbook_depth=50,
    )

    try:

        await feed.run()

    except KeyboardInterrupt:

        print()
        print("Stopping market feed...")

        feed.stop()


if __name__ == "__main__":
    asyncio.run(main())