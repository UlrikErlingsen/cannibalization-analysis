"""Reproducible fictional demonstrations, never presented as business evidence."""
from __future__ import annotations

import numpy as np
import pandas as pd

from shiftsignal.analysis import Launch


def portfolio_demo(context: str = "Restaurant menu") -> tuple[pd.DataFrame, Launch]:
    if context == "Restaurant menu":
        rows = [
            ("Classic burger", 1400, 169, 60, 0.90),
            ("Chicken burger", 850, 179, 64, 0.75),
            ("Plant burger", 500, 175, 68, 0.55),
            ("Steak sandwich", 600, 209, 88, 0.35),
            ("House salad", 650, 149, 48, 0.10),
        ]
        launch = Launch("Smoky mushroom burger", 850, 189, 72, 0.60, 15000)
    else:
        rows = [
            ("Everyday 250 g", 2400, 79, 36, 0.85),
            ("Dark roast 250 g", 1500, 89, 40, 0.75),
            ("Organic 250 g", 1000, 99, 45, 0.95),
            ("Decaf 250 g", 550, 95, 46, 0.15),
            ("Single origin 250 g", 750, 119, 54, 0.65),
        ]
        launch = Launch("Organic dark roast 250 g", 1600, 109, 49, 0.70, 18000)
    return pd.DataFrame(rows, columns=["item", "units", "price", "unit_cost", "overlap"]), launch


def historical_demo(context: str = "Restaurant menu", seed: int = 214) -> tuple[pd.DataFrame, str, str]:
    portfolio, launch = portfolio_demo(context)
    rng = np.random.default_rng(seed)
    dates = pd.date_range("2026-01-05", periods=24, freq="7D")
    launch_date = str(dates[16].date())
    rows = []
    names = list(portfolio.item) + [launch.name]
    prices = list(portfolio.price) + [launch.price]
    costs = list(portfolio.unit_cost) + [launch.unit_cost]
    baseline = portfolio.units.to_numpy() / 20
    donor = (portfolio.units * portfolio.overlap).to_numpy()
    donor = donor / donor.sum()
    for group in ["test", "control"]:
        for location in range(12):
            size = rng.uniform(0.7, 1.3)
            location_effect = rng.normal(0, 0.5, len(baseline))
            for week, date in enumerate(dates):
                demand = baseline * size + 0.6 * week + 3 * np.sin(week / 2) + location_effect
                demand += rng.normal(0, 2, len(baseline))
                new_volume = 0.0
                if week >= 16 and group == "test":
                    new_volume = max(0, launch.units / 20 * size + rng.normal(0, 3))
                    demand -= new_volume * launch.cannibalization * donor
                units = list(np.maximum(0, np.round(demand))) + [round(new_volume)]
                for item, quantity, price, cost in zip(names, units, prices, costs):
                    rows.append({"date": str(date.date()), "location": f"{group}-{location + 1:02}",
                                 "group": group, "item": item, "units": quantity,
                                 "price": price, "unit_cost": cost})
    return pd.DataFrame(rows), launch_date, launch.name
