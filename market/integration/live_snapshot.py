import asyncio

from brain.context.market_state import MarketState
from market.bybit.public_ws import BybitPublicFeed
from market.orderflow import OrderFlowEngine


class LiveMarketSnapshot:

    def __init__(self, symbol: str = "BTCUSDT"):
        self.symbol = symbol.upper()

        self.feed = BybitPublicFeed(
            symbol=self.symbol,
            orderbook_depth=50,
        )

        self.orderflow = OrderFlowEngine()

    def build(self) -> MarketState | None:

        data = self.feed.data

        if data.price is None:
            return None

        flow = self.orderflow.analyze(
            trades=data.trades,
            orderbook_imbalance=data.orderbook_imbalance(),
        )

        return MarketState(
            symbol=self.symbol,
            timestamp=data.last_update,
            price=data.price,

            timeframe="realtime",

            order_flow={
                "buy_volume": flow.buy_volume,
                "sell_volume": flow.sell_volume,
                "delta": flow.delta,
                "cumulative_delta": flow.cumulative_delta,
                "buy_sell_ratio": flow.buy_sell_ratio,
                "bias": flow.bias,
                "aggression": flow.aggression,
                "absorption": flow.absorption,
            },

            orderbook={
                "imbalance": flow.orderbook_imbalance,
                "bid_levels": len(data.bids),
                "ask_levels": len(data.asks),
            },
        )


async def main():

    snapshot = LiveMarketSnapshot("BTCUSDT")

    async def feed_loop():

        await snapshot.feed.run()

    asyncio.create_task(feed_loop())

    print("Waiting for live market data...")

    while True:

        state = snapshot.build()

        if state:

            print()
            print("========== LIVE APEX SNAPSHOT ==========")
            print(f"Symbol:     {state.symbol}")
            print(f"Price:      {state.price:.2f}")

            print(
                f"Delta:      "
                f"{state.order_flow['delta']:.4f}"
            )

            print(
                f"CVD:        "
                f"{state.order_flow['cumulative_delta']:.4f}"
            )

            print(
                f"Buy/Sell:   "
                f"{state.order_flow['buy_sell_ratio']:.2f}"
            )

            print(
                f"OB Imbal:   "
                f"{state.orderbook['imbalance']:+.3f}"
            )

            print(
                f"Bias:       "
                f"{state.order_flow['bias']}"
            )

            print(
                f"Aggression: "
                f"{state.order_flow['aggression']}"
            )

            print(
                f"Absorption: "
                f"{state.order_flow['absorption']}"
            )

            print("========================================")

        await asyncio.sleep(2)


if __name__ == "__main__":
    asyncio.run(main())