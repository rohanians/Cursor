from dataclasses import dataclass
from typing import Any


@dataclass
class MicrostructureSignal:
    bias: str
    score: float
    sweep: str
    absorption: bool
    delta_bias: str
    book_bias: str
    divergence: bool
    reasons: list[str]


class MicrostructureEngine:

    def analyze(
        self,
        state: dict[str, Any],
    ) -> MicrostructureSignal:

        flow = state.get("order_flow", {})
        book = state.get("orderbook", {})
        liquidity = state.get("liquidity", {})

        score_long = 0.0
        score_short = 0.0
        reasons = []

        # -------------------------
        # DELTA / CVD
        # -------------------------

        delta = float(flow.get("delta", 0))
        cvd = float(flow.get("cumulative_delta", 0))

        if delta > 0:
            score_long += 20
            delta_bias = "bullish"
            reasons.append("Positive aggressive delta")

        elif delta < 0:
            score_short += 20
            delta_bias = "bearish"
            reasons.append("Negative aggressive delta")

        else:
            delta_bias = "neutral"

        # -------------------------
        # ORDER BOOK
        # -------------------------

        imbalance = float(
            book.get("imbalance", 0)
        )

        if imbalance > 0.20:

            score_long += 20
            book_bias = "bullish"
            reasons.append(
                "Bid-side liquidity dominance"
            )

        elif imbalance < -0.20:

            score_short += 20
            book_bias = "bearish"
            reasons.append(
                "Ask-side liquidity dominance"
            )

        else:
            book_bias = "neutral"

        # -------------------------
        # LIQUIDITY SWEEP
        # -------------------------

        sweep = str(
            liquidity.get(
                "sweep",
                "none"
            )
        )

        if sweep == "sell_side":

            score_long += 25

            reasons.append(
                "Sell-side liquidity sweep"
            )

        elif sweep == "buy_side":

            score_short += 25

            reasons.append(
                "Buy-side liquidity sweep"
            )

        # -------------------------
        # ABSORPTION
        # -------------------------

        absorption = bool(
            flow.get(
                "absorption",
                False
            )
        )

        if absorption:

            if delta > 0:

                score_long += 15

                reasons.append(
                    "Buy aggression absorbed"
                )

            elif delta < 0:

                score_short += 15

                reasons.append(
                    "Sell aggression absorbed"
                )

        # -------------------------
        # CVD / BOOK DIVERGENCE
        # -------------------------

        divergence = False

        if cvd > 0 and imbalance < -0.30:

            divergence = True

            reasons.append(
                "Positive CVD vs negative book imbalance"
            )

        elif cvd < 0 and imbalance > 0.30:

            divergence = True

            reasons.append(
                "Negative CVD vs positive book imbalance"
            )

        # -------------------------
        # FINAL BIAS
        # -------------------------

        if score_long > score_short:

            bias = "LONG"
            score = score_long

        elif score_short > score_long:

            bias = "SHORT"
            score = score_short

        else:

            bias = "WAIT"
            score = 0.0

        return MicrostructureSignal(
            bias=bias,
            score=min(score, 100),
            sweep=sweep,
            absorption=absorption,
            delta_bias=delta_bias,
            book_bias=book_bias,
            divergence=divergence,
            reasons=reasons,
        )
