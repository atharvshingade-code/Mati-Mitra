
from pathlib import Path

import joblib
import pandas as pd

MODEL_PATH = (
    Path(__file__).resolve().parent
    / "models"
    / "crop_model.joblib"
)


def load_crop_model():
    if not MODEL_PATH.exists():
        raise FileNotFoundError(
            f"Trained crop model not found: {MODEL_PATH}. "
            "Run python train_model.py first."
        )

    return joblib.load(MODEL_PATH)


def predict_crop(
    nitrogen,
    phosphorus,
    potassium,
    temperature,
    humidity,
    ph,
    rainfall,
    top_n=3,
):
    bundle = load_crop_model()
    model = bundle["model"]
    features = bundle["features"]

    values = {
        "N": nitrogen,
        "P": phosphorus,
        "K": potassium,
        "temperature": temperature,
        "humidity": humidity,
        "ph": ph,
        "rainfall": rainfall,
    }

    inputs = pd.DataFrame(
        [[values[name] for name in features]],
        columns=features,
    )

    prediction = str(model.predict(inputs)[0])

    probabilities = model.predict_proba(inputs)[0]
    ranked = sorted(
        zip(model.classes_, probabilities),
        key=lambda item: item[1],
        reverse=True,
    )[:max(1, min(int(top_n), len(model.classes_)))]

    return {
        "predicted_crop": prediction,
        "model_probability": float(
            probabilities[list(model.classes_).index(prediction)]
        ),
        "alternatives": [
            {
                "crop": str(crop),
                "model_probability": float(probability),
            }
            for crop, probability in ranked
        ],
        "model_test_accuracy": float(bundle["test_accuracy"]),
        "disclaimer": (
            "Predictions are based on the training dataset and "
            "do not guarantee real-world crop suitability."
        ),
    }
