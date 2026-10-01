import os
import numpy as np
import pandas as pd

def generate_voting_dataset(num_samples=1_000_000, anomaly_fraction=0.20, random_state=42):
    """
    Generates synthetic voter interaction sessions (default 1M records) across 12 feature parameters.
    Uses fast vectorized NumPy ops for sub-second generation speed.
    """
    np.random.seed(random_state)
    
    num_anomalies = int(num_samples * anomaly_fraction)
    num_normal = num_samples - num_anomalies
    
    # --- 1. Vectorized Generation of Normal Voting Patterns ---
    normal_data = {
        'voter_age': np.random.randint(18, 85, size=num_normal),
        'time_delta_sec': np.random.normal(loc=25.0, scale=7.0, size=num_normal).clip(8.0, 120.0).round(2),
        'login_frequency_last_hour': np.random.poisson(lam=1.2, size=num_normal).clip(1, 4),
        'face_match_confidence': np.random.normal(loc=0.93, scale=0.04, size=num_normal).clip(0.75, 0.99).round(4),
        'failed_otp_attempts': np.random.choice([0, 1], p=[0.94, 0.06], size=num_normal),
        'ip_risk_score': np.random.uniform(0.01, 0.30, size=num_normal).round(4),
        'device_change_count': np.random.choice([0, 1], p=[0.88, 0.12], size=num_normal),
        # 5 New Realistic Feature Parameters
        'keystroke_delay_ms': np.random.normal(loc=210.0, scale=40.0, size=num_normal).clip(100.0, 450.0).round(1),
        'mouse_movement_entropy': np.random.normal(loc=0.88, scale=0.05, size=num_normal).clip(0.70, 0.99).round(4),
        'face_liveness_score': np.random.normal(loc=0.94, scale=0.03, size=num_normal).clip(0.80, 0.99).round(4),
        'is_vpn_or_proxy': np.random.choice([0, 1], p=[0.96, 0.04], size=num_normal),
        'viewport_screen_ratio': np.random.normal(loc=0.92, scale=0.04, size=num_normal).clip(0.80, 1.00).round(4),
        'is_anomaly': np.zeros(num_normal, dtype=int)
    }
    
    # --- 2. Vectorized Generation of Diverse Anomalous/Fraudulent Patterns ---
    # Split anomalies equally across 5 threat patterns
    n_per_threat = num_anomalies // 5
    remainder = num_anomalies % 5
    
    # Base baseline for anomalies
    age_a = np.random.randint(18, 85, size=num_anomalies)
    delta_a = np.random.normal(loc=25.0, scale=7.0, size=num_anomalies).clip(8.0, 120.0)
    freq_a = np.random.poisson(lam=1.2, size=num_anomalies).clip(1, 4)
    face_a = np.random.normal(loc=0.93, scale=0.04, size=num_anomalies).clip(0.75, 0.99)
    otp_a = np.random.choice([0, 1], p=[0.90, 0.10], size=num_anomalies)
    ip_a = np.random.uniform(0.01, 0.30, size=num_anomalies)
    dev_a = np.random.choice([0, 1], p=[0.85, 0.15], size=num_anomalies)
    keys_a = np.random.normal(loc=210.0, scale=40.0, size=num_anomalies).clip(100.0, 450.0)
    mouse_a = np.random.normal(loc=0.88, scale=0.05, size=num_anomalies).clip(0.70, 0.99)
    live_a = np.random.normal(loc=0.94, scale=0.03, size=num_anomalies).clip(0.80, 0.99)
    vpn_a = np.random.choice([0, 1], p=[0.90, 0.10], size=num_anomalies)
    view_a = np.random.normal(loc=0.92, scale=0.04, size=num_anomalies).clip(0.80, 1.00)
    
    # Threat 1: OTP Brute Force (High failed OTP, high login freq, fast key delay)
    idx1 = slice(0, n_per_threat)
    otp_a[idx1] = np.random.randint(2, 6, size=n_per_threat)
    freq_a[idx1] = np.random.randint(4, 12, size=n_per_threat)
    keys_a[idx1] = np.random.uniform(5.0, 35.0, size=n_per_threat)
    
    # Threat 2: Biometric Spoof & Photo Replay Attack (Low face match, low liveness)
    idx2 = slice(n_per_threat, 2 * n_per_threat)
    face_a[idx2] = np.random.uniform(0.30, 0.68, size=n_per_threat)
    live_a[idx2] = np.random.uniform(0.15, 0.55, size=n_per_threat)
    
    # Threat 3: Rapid Bot Execution & Headless Scraper (Ultrast rapid speed, low mouse entropy, weird viewport)
    idx3 = slice(2 * n_per_threat, 3 * n_per_threat)
    delta_a[idx3] = np.random.uniform(0.1, 3.5, size=n_per_threat)
    freq_a[idx3] = np.random.randint(6, 25, size=n_per_threat)
    mouse_a[idx3] = np.random.uniform(0.01, 0.25, size=n_per_threat)
    view_a[idx3] = np.random.uniform(0.20, 0.55, size=n_per_threat)
    keys_a[idx3] = np.random.uniform(0.0, 15.0, size=n_per_threat)
    
    # Threat 4: Proxy / VPN & Multi-Device Hijack (High IP risk, VPN enabled, device changes)
    idx4 = slice(3 * n_per_threat, 4 * n_per_threat)
    ip_a[idx4] = np.random.uniform(0.68, 0.99, size=n_per_threat)
    vpn_a[idx4] = 1
    dev_a[idx4] = np.random.randint(2, 5, size=n_per_threat)
    
    # Threat 5: Multi-Factor Attack (Combined vector anomalies)
    idx5 = slice(4 * n_per_threat, num_anomalies)
    otp_a[idx5] = np.random.randint(2, 5, size=num_anomalies - 4 * n_per_threat)
    face_a[idx5] = np.random.uniform(0.35, 0.70, size=num_anomalies - 4 * n_per_threat)
    live_a[idx5] = np.random.uniform(0.20, 0.60, size=num_anomalies - 4 * n_per_threat)
    delta_a[idx5] = np.random.uniform(0.1, 4.0, size=num_anomalies - 4 * n_per_threat)
    ip_a[idx5] = np.random.uniform(0.60, 0.98, size=num_anomalies - 4 * n_per_threat)
    vpn_a[idx5] = 1
    dev_a[idx5] = np.random.randint(2, 5, size=num_anomalies - 4 * n_per_threat)
    
    anomaly_data = {
        'voter_age': age_a,
        'time_delta_sec': delta_a.round(2),
        'login_frequency_last_hour': freq_a,
        'face_match_confidence': face_a.round(4),
        'failed_otp_attempts': otp_a,
        'ip_risk_score': ip_a.round(4),
        'device_change_count': dev_a,
        'keystroke_delay_ms': keys_a.round(1),
        'mouse_movement_entropy': mouse_a.round(4),
        'face_liveness_score': live_a.round(4),
        'is_vpn_or_proxy': vpn_a,
        'viewport_screen_ratio': view_a.round(4),
        'is_anomaly': np.ones(num_anomalies, dtype=int)
    }
    
    df_normal = pd.DataFrame(normal_data)
    df_anomaly = pd.DataFrame(anomaly_data)
    
    df = pd.concat([df_normal, df_anomaly], ignore_index=True)
    df = df.sample(frac=1.0, random_state=random_state).reset_index(drop=True)
    
    os.makedirs('voting_datasets', exist_ok=True)
    output_path = os.path.join('voting_datasets', 'voter_activity_dataset.csv')
    df.to_csv(output_path, index=False)
    print(f"1M Dataset generated successfully with {len(df)} samples ({num_anomalies} anomalies, 12 features) at '{output_path}'.")
    return df

if __name__ == "__main__":
    generate_voting_dataset(num_samples=1_000_000)
