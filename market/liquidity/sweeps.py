from dataclasses import dataclass


@dataclass
class LiquiditySweep:
    detected: bool
    direction: str
    level: float | None
    reclaim: bool
    rejection: bool
    strength: float


class LiquiditySweepDetector:

    def detect(
        self,
        price: float,
        previous_low: float | None,
        previous_high: float | None,
        delta: float,
    ) -> LiquiditySweep:

        if previous_low is not None and price < previous_low:

            reclaim = price > previous_low

            strength = min(
                abs(delta) / max(abs(price), 1),
                1.0,
            )

            return LiquiditySweep(
                detected=True,
                direction="sell_side",
                level=previous_low,
                reclaim=reclaim,
                rejection=True,
                strength=strength,
            )

        if previous_high is not None and price > previous_high:

            reclaim = price < previous_high

            strength = min(
                abs(delta) / max(abs(price), 1),
                1.0,
            )

            return LiquiditySweep(
                detected=True,
                direction="buy_side",
                level=previous_high,
                reclaim=reclaim,
                rejection=True,
                strength=strength,
            )

        return LiquiditySweep(
            detected=False,
            direction="none",
            level=None,
            reclaim=False,
            rejection=False,
            strength=0.0,
        )
