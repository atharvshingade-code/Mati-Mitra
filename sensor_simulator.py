
"""Synthetic sensor readings for the Jarvis for Farmers demo."""

from datetime import datetime
import random


def initial_readings():
    return {
        "N": round(random.uniform(25, 100), 1),
        "P": round(random.uniform(15, 80), 1),
        "K": round(random.uniform(20, 100), 1),
        "temperature": round(random.uniform(18, 35), 2),
        "humidity": round(random.uniform(40, 95), 2),
        "pH": round(random.uniform(5.5, 7.8), 2),
        "rainfall": round(random.uniform(50, 250), 2),
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "source": "SIMULATED",
    }


def next_readings(previous):
    result = {}

    # Illustrative demo values, not calibrated real-world sensor readings.
    for nutrient in ("N", "P", "K"):
        result[nutrient] = round(
            max(
                0,
                min(
                    140,
                    float(previous[nutrient]) + random.uniform(-3, 3),
                ),
            ),
            1,
        )

    result["temperature"] = round(
        max(
            10,
            min(
                45,
                float(previous["temperature"]) + random.uniform(-1, 1),
            ),
        ),
        2,
    )

    result["humidity"] = round(
        max(
            10,
            min(
                100,
                float(previous["humidity"]) + random.uniform(-3, 3),
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
                float(previous["rainfall"]) + random.uniform(-10, 10),
            ),
        ),
        2,
    )

    result["timestamp"] = datetime.now().isoformat(timespec="seconds")
    result["source"] = "SIMULATED"

    return result
