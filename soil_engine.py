
"""Transparent soil interpretation and screening alerts for MatiMitra.

NPK bands are illustrative demo values, not validated agronomic thresholds.
Alerts are screening checks, not definitive diagnoses.
"""

import math

# Demo-only bands. These are NOT universal agronomic thresholds.
DEMO_BANDS = {
    "N": (40, 80),
    "P": (30, 60),
    "K": (35, 75),
}

# Broad input checks for screening only, not crop-specific recommendations.
VALID_RANGES = {
    "N": (0, 1000),
    "P": (0, 1000),
    "K": (0, 1000),
    "pH": (0, 14),
    "temperature": (-10, 60),
    "humidity": (0, 100),
    "rainfall": (0, 1000),
    "moisture": (0, 100),
}


def _to_number(value):
    """Convert a value to a finite float, or return None."""
    try:
        number = float(value)
        if not math.isfinite(number):
            return None
        return number
    except (TypeError, ValueError):
        return None


def classify_demo_value(nutrient, value):
    """Classify NPK values using illustrative demo bands."""
    if nutrient not in DEMO_BANDS:
        return {"status": "Unknown", "marathi": "अज्ञात"}

    number = _to_number(value)
    if number is None:
        return {"status": "Invalid", "marathi": "अवैध"}

    low, high = DEMO_BANDS[nutrient]

    if number < low:
        return {"status": "Low", "marathi": "कमी"}
    if number <= high:
        return {"status": "Moderate", "marathi": "मध्यम"}

    return {"status": "High", "marathi": "जास्त"}


def analyze_soil(readings):
    """Return soil interpretations without inventing missing measurements."""
    result = {}

    for nutrient in ("N", "P", "K"):
        value = _to_number(readings.get(nutrient))

        if value is None:
            result[nutrient] = {
                "value": None,
                "status": "Missing or invalid",
                "marathi": "माहिती उपलब्ध नाही किंवा अवैध",
            }
            continue

        item = classify_demo_value(nutrient, value)
        item["value"] = value
        result[nutrient] = item

    ph = _to_number(readings.get("pH"))

    if ph is None or not 0 <= ph <= 14:
        result["pH"] = {
            "value": ph,
            "status": "Missing or invalid",
        }
    else:
        if ph < 4.5:
            ph_status = "Extremely acidic"
        elif ph < 5.5:
            ph_status = "Strongly acidic"
        elif ph < 6.5:
            ph_status = "Acidic"
        elif ph <= 7.5:
            ph_status = "Near neutral"
        elif ph <= 8.5:
            ph_status = "Alkaline"
        else:
            ph_status = "Strongly alkaline"

        result["pH"] = {
            "value": ph,
            "status": ph_status,
        }

    result["limitations"] = (
        "Synthetic NPK values have no calibrated concentration units. "
        "NPK bands are illustrative and must not determine real fertilizer "
        "doses. Confirm soil status using a reliable soil test."
    )

    return result


def generate_soil_alerts(readings):
    """Return screening alerts for missing, invalid, or unusual readings."""
    alerts = []

    if not isinstance(readings, dict):
        return ["Readings are unavailable. Check the data source."]

    # Required core readings.
    for key in ("N", "P", "K", "pH"):
        value = _to_number(readings.get(key))

        if value is None:
            alerts.append(
                f"{key}: reading is missing or invalid. Check the input "
                "or measurement source."
            )
            continue

        minimum, maximum = VALID_RANGES[key]
        if not minimum <= value <= maximum:
            alerts.append(
                f"{key}: reading is outside the accepted input range. "
                "Check the value or measurement device."
            )
            continue

        if key in DEMO_BANDS:
            low, high = DEMO_BANDS[key]
            if value < low or value > high:
                alerts.append(
                    f"{key}: reading is outside the illustrative demo "
                    f"band ({low}-{high}). This is not proof of a "
                    "nutrient deficiency or excess."
                )

        elif key == "pH":
            if value < 4.5:
                alerts.append(
                    "pH: extremely acidic reading. Verify with a reliable "
                    "soil test before making decisions."
                )
            elif value < 5.5:
                alerts.append(
                    "pH: acidic reading. Confirm with a reliable soil test."
                )
            elif value > 8.5:
                alerts.append(
                    "pH: alkaline reading. Confirm with a reliable soil test."
                )

    # Check optional environmental readings only when supplied.
    optional_names = {
        "temperature": "Temperature",
        "humidity": "Humidity",
        "rainfall": "Rainfall",
        "moisture": "Soil moisture",
    }

    for key, label in optional_names.items():
        if key not in readings or readings[key] is None:
            continue

        value = _to_number(readings[key])

        if value is None:
            alerts.append(
                f"{label}: invalid reading. Check the input or sensor."
            )
            continue

        minimum, maximum = VALID_RANGES[key]
        if not minimum <= value <= maximum:
            alerts.append(
                f"{label}: value is outside the configured input range. "
                "Check the reading or sensor."
            )

    if not alerts:
        alerts.append(
            "No configured screening issues detected. This does not "
            "confirm that the soil is healthy or that sensors are accurate."
        )

    return alerts
