def format_coins(amount: float) -> str:
    if amount >= 1_000_000:
        return f"~{amount / 1_000_000:.1f}M"
    if amount >= 1_000:
        return f"~{amount / 1_000:.0f}k"
    return str(int(amount))
