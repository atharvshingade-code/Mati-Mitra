
"""Synthetic sensor readings for the MatiMitra demo."""

from datetime import datetime
import random


def initial_readings():
    """Create the first simulated reading."""
    return {
        "N": round(random.uniform(45, 100), 1),
        "P": round(random.uniform(20, 80), 1),
        "K": round(random.uniform(25, 100), 1),
        "temperature": round(random.uniform(18, 35), 2),
        "humidity": round(random.uniform(40, 95), 2),
        "pH": round(random.uniform(5.5, 7.8), 2),
        "rainfall": round(random.uniform(50, 250), 2),
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "source": "SIMULATED",
    }


def next_readings(previous, nitrogen_decline=False):
    """
    Generate the next simulated reading.

    nitrogen_decline=True reduces nitrogen by 10% per step for
    testing MatiMitra's trend-alert mechanism.

    These values are demonstrations, not real sensor measurements
    or validated agricultural thresholds.
    """
    result = {}

    for nutrient in ("N", "P", "K"):
        previous_value = float(previous[nutrient])

        if nutrient == "N" and nitrogen_decline:
            new_value = previous_value * 0.90
        else:
            new_value = previous_value + random.uniform(-3, 3)

        result[nutrient] = round(max(0, min(140, new_value)), 1)

    result["temperature"] = round(
        max(
            10,
            min(
                45,
                float(previous.get("temperature", 25))
                + random.uniform(-1, 1),
            ),
        ),
        2,
    )

    result["humidity"] = round(
        max(
            10,
            min(
                100,
                float(previous.get("humidity", 60))
                + random.uniform(-3, 3),
            ),
        ),
        2,
    )

    result["pH"] = round(
        max(
            4.5,
            min(
                9.0,
                float(previous["pH"]) + random.uniform(-0.08, 0.08),
            ),
        ),
        2,
    )

    result["rainfall"] = round(
        max(
            0,
            min(
                300,
                float(previous.get("rainfall", 100))
                + random.uniform(-10, 10),
            ),
        ),
        2,
    )

    result["timestamp"] = datetime.now().isoformat(timespec="seconds")
    result["source"] = "SIMULATED"

    return result
