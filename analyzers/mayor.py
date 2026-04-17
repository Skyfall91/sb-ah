from __future__ import annotations
from dataclasses import dataclass
from typing import Optional
from models import Opportunity
import statistics


@dataclass
class MayorCycle:
    mayor: str
    start_day: int
    end_day: int


class MayorAnalyzer:
    def __init__(self, min_cycles: int = 3, min_avg_increase_pct: float = 50.0, min_profit: float = 100_000):
        self.min_cycles = min_cycles
        self.min_avg_increase_pct = min_avg_increase_pct
        self.min_profit = min_profit

    def analyze_item(
        self,
        item_id: str,
        item_name: str,
        history: list,
        cycles: list,
        current_mayor: str,
    ) -> Optional[Opportunity]:
        matching = [c for c in cycles if c.mayor == current_mayor]
        if len(matching) < self.min_cycles:
            return None

        prices = [entry["avg"] for entry in history]
        if not prices:
            return None

        overall_avg = statistics.mean(prices)

        cycle_increases = []
        for cycle in matching:
            cycle_prices = prices[cycle.start_day:cycle.end_day + 1]
            if not cycle_prices:
                continue
            cycle_avg = statistics.mean(cycle_prices)
            pct_increase = ((cycle_avg - overall_avg) / overall_avg) * 100
            cycle_increases.append(pct_increase)

        if len(cycle_increases) < self.min_cycles:
            return None

        avg_increase = statistics.mean(cycle_increases)
        if avg_increase < self.min_avg_increase_pct:
            return None

        current_price = prices[-1] if prices else overall_avg
        projected_price = current_price * (1 + avg_increase / 100)
        projected_profit_per_item = projected_price - current_price

        if projected_profit_per_item < self.min_profit:
            return None

        confidence = "high" if avg_increase > 100 else "medium"

        return Opportunity(
            type="MAYOR",
            item_id=item_id,
            item_name=item_name,
            profit=projected_profit_per_item,
            action="JETZT INVESTIEREN",
            details={
                "current_mayor": current_mayor,
                "current_price": round(current_price),
                "avg_increase_pct": round(avg_increase, 1),
                "cycles_analyzed": len(cycle_increases),
                "projected_price": round(projected_price),
            },
            confidence=confidence,
        )
