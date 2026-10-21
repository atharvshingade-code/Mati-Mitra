
from pathlib import Path

import joblib
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
)
from sklearn.model_selection import train_test_split

BASE_DIR = Path(__file__).resolve().parent
DATA_PATH = BASE_DIR / "data" / "Crop_recommendation.csv"
MODEL_DIR = BASE_DIR / "models"
MODEL_PATH = MODEL_DIR / "crop_model.joblib"

FEATURES = [
    "N",
    "P",
    "K",
    "temperature",
    "humidity",
    "ph",
    "rainfall",
]
TARGET = "label"


def main():
    if not DATA_PATH.exists():
        raise FileNotFoundError(f"Dataset not found: {DATA_PATH}")

    data = pd.read_csv(DATA_PATH)

    required = FEATURES + [TARGET]
    missing = set(required) - set(data.columns)
    if missing:
        raise ValueError(f"Missing dataset columns: {sorted(missing)}")

    if data[required].isnull().any().any():
        raise ValueError("Dataset contains missing values.")

    X = data[FEATURES]
    y = data[TARGET]

    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=0.20,
        random_state=42,
        stratify=y,
    )

    model = RandomForestClassifier(
        n_estimators=300,
        random_state=42,
        class_weight="balanced",
        n_jobs=-1,
    )
    model.fit(X_train, y_train)

    predictions = model.predict(X_test)
    accuracy = accuracy_score(y_test, predictions)

    print(f"Dataset rows: {len(data)}")
    print(f"Training rows: {len(X_train)}")
    print(f"Test rows: {len(X_test)}")
    print(f"Number of crop classes: {y.nunique()}")
    print(f"Test accuracy: {accuracy:.4%}")
    print("\nClassification report:")
    print(classification_report(y_test, predictions, zero_division=0))
    print("\nConfusion matrix:")
    print(confusion_matrix(y_test, predictions))

    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump(
        {
            "model": model,
            "features": FEATURES,
            "classes": model.classes_.tolist(),
            "dataset_rows": len(data),
            "test_accuracy": accuracy,
            "random_state": 42,
        },
        MODEL_PATH,
    )

    print(f"\nModel saved to: {MODEL_PATH}")


if __name__ == "__main__":
    main()
