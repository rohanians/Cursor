from brain.context.market_state import MarketState


def build_context(state: MarketState) -> dict:
    """
    Convert the current market state into the context
    that will eventually be supplied to the APEX Brain.
    """

    return {
        "market": state.to_dict(),
        "task": "Evaluate the current market for a valid APEX setup.",
    }