
"""Synthetic sensor readings for the Jarvis for Farmers demo."""

from datetime import datetime
import random

def initial_readings():
    return {
        "N": round(random.uniform(25, 100), 1),
        "P": round(random.uniform(15, 80), 1),
        "K": round(random.uniform(20, 100), 1),
        "pH": round(random.uniform(5.5, 7.8), 2),
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "source": "SIMULATED",
    }


def next_readings(previous):
    result = {}

    # These are illustrative demo values, not calibrated concentrations.
    for nutrient in ("N", "P", "K"):
        result[nutrient] = round(
            max(0, min(140, float(previous[nutrient]) + random.uniform(-3, 3))),
            1,
        )

    result["pH"] = round(
        max(4.5, min(9.0, float(previous["pH"]) + random.uniform(-0.08, 0.08))),
        2,
    )
    result["timestamp"] = datetime.now().isoformat(timespec="seconds")
    result["source"] = "SIMULATED"
    return result
