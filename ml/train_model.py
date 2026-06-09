import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import accuracy_score, classification_report
import joblib
import os
from pathlib import Path

# Paths
_ROOT = Path(__file__).parent.parent
DATA_PATH = _ROOT / "dataset.csv" if (_ROOT / "dataset.csv").exists() else _ROOT / "data" / "dataset.csv"
MODEL_DIR = _ROOT / "ml"
MODEL_PATH = MODEL_DIR / "churn_model.pkl"

def main():
    if not DATA_PATH.exists():
        print(f"Dataset not found at {DATA_PATH}")
        return

    print(f"Loading data from {DATA_PATH}...")
    df = pd.read_csv(DATA_PATH)
    
    # The dataset has no actual attrition flag, so we use the proxy (utilization > 0.7)
    print("Preprocessing data...")
    if 'Average_Utilization_Ratio' not in df.columns:
        print("Error: 'Average_Utilization_Ratio' column not found in dataset. Ensure dataset is correct.")
        return
        
    df['churn'] = (df['Average_Utilization_Ratio'] > 0.7).astype(int)
    
    # Drop irrelevant or target-leaking columns
    cols_to_drop = ['clientID', 'churn', 'Average_Utilization_Ratio']
    
    # Identify categorical and numerical columns
    categorical_cols = df.select_dtypes(include=['object']).columns.tolist()
    categorical_cols = [c for c in categorical_cols if c not in cols_to_drop]
    
    # We will use simple Label Encoding for categorical features
    encoders = {}
    for col in categorical_cols:
        le = LabelEncoder()
        df[col] = df[col].astype(str)
        df[col] = le.fit_transform(df[col])
        encoders[col] = le
        
    X = df.drop(columns=[c for c in cols_to_drop if c in df.columns])
    y = df['churn']
    
    # Fill any missing values with 0
    X = X.fillna(0)
    
    # Split
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    
    print(f"Training Random Forest on {len(X_train)} samples...")
    model = RandomForestClassifier(n_estimators=100, random_state=42, n_jobs=-1)
    model.fit(X_train, y_train)
    
    print("Evaluating model...")
    y_pred = model.predict(X_test)
    acc = accuracy_score(y_test, y_pred)
    print(f"Accuracy: {acc:.4f}")
    print(classification_report(y_test, y_pred))
    
    # Save the model, encoders, and feature names
    print(f"Saving model to {MODEL_PATH}...")
    MODEL_DIR.mkdir(exist_ok=True)
    
    # Calculate feature importances
    importances = model.feature_importances_
    feature_importances = dict(zip(X.columns, importances))
    
    model_artifact = {
        'model': model,
        'encoders': encoders,
        'features': X.columns.tolist(),
        'importances': feature_importances,
        'metrics': {
            'accuracy': acc
        }
    }
    
    joblib.dump(model_artifact, MODEL_PATH)
    print("Done!")

if __name__ == "__main__":
    main()
