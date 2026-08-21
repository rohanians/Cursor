
from dataclasses import dataclass, field

@dataclass

class RiskResult:

    approved: bool

    reasons: list[str] = field(default_factory=list)

class RiskGate:

    def __init__(

        self,

        account_size: float = 500.0,

        risk_per_trade_pct: float = 1.0,

        max_leverage: float = 5.0,

        max_concurrent_positions: int = 2,

        daily_drawdown_kill_pct: float = 3.0,

        min_confidence: float = 75.0,

    ):

        self.account_size = account_size

        self.risk_per_trade_pct = risk_per_trade_pct

        self.max_leverage = max_leverage

        self.max_concurrent_positions = max_concurrent_positions

        self.daily_drawdown_kill_pct = daily_drawdown_kill_pct

        self.min_confidence = min_confidence

        self.killed = False

    def kill(self) -> None:

        self.killed = True

    def reset_kill(self) -> None:

        self.killed = False

    def evaluate(

        self,

        decision,

        current_positions: int = 0,

        daily_drawdown_pct: float = 0.0,

        requested_leverage: float = 1.0,

    ) -> RiskResult:

        reasons = []

        if self.killed:

            return RiskResult(False, ["SYSTEM KILL SWITCH ACTIVE"])

        if decision.action == "WAIT":

            return RiskResult(False, ["Decision is WAIT"])

        if decision.confidence < self.min_confidence:

            return RiskResult(False, ["Confidence below risk threshold"])

        if decision.entry is None or decision.stop_loss is None:

            return RiskResult(False, ["Missing entry or stop loss"])

        if requested_leverage > self.max_leverage:

            return RiskResult(False, ["Requested leverage exceeds maximum"])

        if current_positions >= self.max_concurrent_positions:

            return RiskResult(False, ["Maximum concurrent positions reached"])

        if daily_drawdown_pct >= self.daily_drawdown_kill_pct:

            self.killed = True

            return RiskResult(False, ["Daily drawdown kill threshold reached"])

        stop_distance = abs(decision.entry - decision.stop_loss)

        if stop_distance <= 0:

            return RiskResult(False, ["Invalid stop-loss distance"])

        reasons.append("Confidence approved")

        reasons.append("Position limit approved")

        reasons.append("Leverage approved")

        reasons.append("Drawdown approved")

        reasons.append("Stop-loss present")

        return RiskResult(True, reasons)

