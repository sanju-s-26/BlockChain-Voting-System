import os
import joblib
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier, IsolationForest
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import classification_report, accuracy_score, confusion_matrix

def train_and_export_models():
    dataset_path = os.path.join('voting_datasets', 'voter_activity_dataset.csv')
    if not os.path.exists(dataset_path):
        from generate_dataset import generate_voting_dataset
        generate_voting_dataset(num_samples=1_000_000)
        
    print(f"Loading dataset from '{dataset_path}'...")
    df = pd.read_csv(dataset_path)
    print(f"Loaded dataset with shape {df.shape}")
    
    feature_cols = [
        'voter_age',
        'time_delta_sec',
        'login_frequency_last_hour',
        'face_match_confidence',
        'failed_otp_attempts',
        'ip_risk_score',
        'device_change_count',
        'keystroke_delay_ms',
        'mouse_movement_entropy',
        'face_liveness_score',
        'is_vpn_or_proxy',
        'viewport_screen_ratio'
    ]
    
    X = df[feature_cols]
    y = df['is_anomaly']
    
    print("Splitting dataset into 80% training / 20% testing subsets...")
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)
    
    print("Fitting StandardScaler on 12 feature vectors...")
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)
    
    # 1. Random Forest Classifier (Multi-threaded with n_jobs=-1)
    print("Training Random Forest Classifier on 800,000 samples (n_estimators=100, max_depth=15, n_jobs=-1)...")
    rf_model = RandomForestClassifier(n_estimators=100, max_depth=15, n_jobs=-1, random_state=42)
    rf_model.fit(X_train_scaled, y_train)
    
    print("Evaluating Random Forest Model on 200,000 test samples...")
    rf_preds = rf_model.predict(X_test_scaled)
    acc = accuracy_score(y_test, rf_preds)
    print("\n--- Random Forest Classifier Performance ---")
    print(f"Accuracy: {acc * 100:.2f}%")
    print(classification_report(y_test, rf_preds, digits=4))
    
    # Feature Importances
    importances = dict(zip(feature_cols, rf_model.feature_importances_))
    print("Feature Importances (12 Parameters):")
    for f, imp in sorted(importances.items(), key=lambda x: x[1], reverse=True):
        print(f"  - {f}: {imp:.4f}")
        
    # MLOps: MLflow Experiment & Model Registry Tracking
    try:
        import mlflow
        import mlflow.sklearn
        mlflow.set_experiment("SmartVote_MLOps_Anomaly_Classifier")
        with mlflow.start_run(run_name="rf_classifier_training"):
            mlflow.log_params({
                "n_estimators": 100,
                "max_depth": 15,
                "dataset_samples": len(df),
                "features_count": len(feature_cols)
            })
            mlflow.log_metric("accuracy", acc)
            for f, imp in importances.items():
                mlflow.log_metric(f"importance_{f}", float(imp))
            mlflow.sklearn.log_model(rf_model, "rf_model")
            print("[MLflow MLOps] Successfully logged experiment metrics and model registry artifact!")
    except Exception as e:
        print(f"[MLflow MLOps] Optional experiment tracking offline: {e}")

    # 2. Isolation Forest Anomaly Detector (Baseline Unsupervised Model)
    print("\nTraining Isolation Forest on training subset...")
    iso_forest = IsolationForest(contamination=0.20, n_jobs=-1, random_state=42)
    iso_forest.fit(X_train_scaled)
    
    # Save artifacts
    os.makedirs('ml_module', exist_ok=True)
    joblib.dump(rf_model, os.path.join('ml_module', 'rf_model.joblib'))
    joblib.dump(scaler, os.path.join('ml_module', 'scaler.joblib'))
    joblib.dump(iso_forest, os.path.join('ml_module', 'iso_forest.joblib'))
    
    print("\nModels and Scaler exported successfully to 'ml_module/' directory.")

if __name__ == "__main__":
    train_and_export_models()
