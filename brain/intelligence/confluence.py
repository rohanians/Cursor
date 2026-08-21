from dataclasses import dataclass
from typing import Any


@dataclass
class ConfluenceResult:
    bias: str
    score: float
    approved: bool
    reasons: list[str]
    blockers: list[str]


class ConfluenceEngine:

    MIN_SCORE = 75.0

    def evaluate(
        self,
        market: dict[str, Any],
        microstructure: dict[str, Any],
    ) -> ConfluenceResult:

        long_score = 0.0
        short_score = 0.0

        reasons = []
        blockers = []

        # -------------------------
        # MICROSTRUCTURE
        # -------------------------

        micro_bias = microstructure.get(
            "bias",
            "WAIT"
        )

        micro_score = float(
            microstructure.get(
                "score",
                0
            )
        )

        if micro_bias == "LONG":

            long_score += micro_score

        elif micro_bias == "SHORT":

            short_score += micro_score

        # -------------------------
        # STRUCTURE
        # -------------------------

        structure = market.get(
            "structure",
            {}
        )

        structure_bias = str(
            structure.get(
                "bias",
                ""
            )
        ).upper()

        if structure_bias == "BULLISH":

            long_score += 20
            reasons.append(
                "Higher-timeframe structure bullish"
            )

        elif structure_bias == "BEARISH":

            short_score += 20
            reasons.append(
                "Higher-timeframe structure bearish"
            )

        # -------------------------
        # OI
        # -------------------------

        oi = market.get(
            "open_interest",
            {}
        )

        oi_change = float(
            oi.get(
                "change_pct",
                0
            )
        )

        if oi_change >= 3:

            if long_score > short_score:

                long_score += 10

            elif short_score > long_score:

                short_score += 10

            reasons.append(
                f"OI expanding {oi_change:.2f}%"
            )

        # -------------------------
        # RVOL
        # -------------------------

        volume = market.get(
            "volume",
            {}
        )

        rvol = float(
            volume.get(
                "rvol",
                0
            )
        )

        if rvol >= 3:

            if long_score > short_score:

                long_score += 5

            elif short_score > long_score:

                short_score += 5

            reasons.append(
                f"High RVOL {rvol:.2f}x"
            )

        # -------------------------
        # FINAL
        # -------------------------

        if long_score > short_score:

            bias = "LONG"
            score = min(long_score, 100)

        elif short_score > long_score:

            bias = "SHORT"
            score = min(short_score, 100)

        else:

            bias = "WAIT"
            score = 0

        approved = (
            bias != "WAIT"
            and score >= self.MIN_SCORE
        )

        if not approved:

            blockers.append(
                f"Confluence below "
                f"{self.MIN_SCORE:.0f}"
            )

        return ConfluenceResult(
            bias=bias,
            score=score,
            approved=approved,
            reasons=reasons,
            blockers=blockers,
        )
