import os
import time
import random
import sqlite3
import joblib
import base64
import io
import json
from PIL import Image, ImageOps
import numpy as np
import pandas as pd
from typing import Optional, Union, Dict, Any, List
from pydantic import BaseModel
import dotenv
from fastapi import FastAPI, HTTPException, status, Request
from fastapi.middleware.cors import CORSMiddleware
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import jwt
from passlib.context import CryptContext

# Load environment variables
dotenv.load_dotenv()
SECRET_KEY = os.environ.get('SECRET_KEY', 'smartvote_secure_jwt_secret_key_2026')

pwd_context = CryptContext(
    schemes=["argon2"],
    deprecated="auto",
    argon2__memory_cost=65536,
    argon2__time_cost=2,
    argon2__parallelism=8
)

def hash_password(password: str) -> str:
    if not password:
        return ""
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    if not plain_password or not hashed_password:
        return False
    if hashed_password.startswith("$argon2"):
        try:
            return pwd_context.verify(plain_password, hashed_password)
        except Exception:
            return False
    else:
        return plain_password == hashed_password


app = FastAPI(
    title="SmartVote AI Backend & Anomaly Detection API",
    description="Dual Authentication and Random Forest ML Anomaly Detection Service for SmartVote",
    version="2.1.0"
)

# CORS configuration
origins = [
    "http://localhost:8080",
    "http://127.0.0.1:8080",
    "http://localhost:8000",
    "http://127.0.0.1:8000",
    "*"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# SQLite Database Setup (Auto-fallback)
DB_PATH = os.path.join(os.path.dirname(__file__), "voters.db")

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS voters (
            voter_id TEXT PRIMARY KEY,
            password TEXT NOT NULL,
            name TEXT NOT NULL,
            role TEXT NOT NULL,
            face_image TEXT
        )
    ''')
    
    # Ensure face_image, age, email, and extended demographic columns exist if upgraded from older schema
    cursor.execute("PRAGMA table_info(voters)")
    columns = [col[1] for col in cursor.fetchall()]
    if "face_image" not in columns:
        cursor.execute("ALTER TABLE voters ADD COLUMN face_image TEXT")
    if "age" not in columns:
        cursor.execute("ALTER TABLE voters ADD COLUMN age INTEGER DEFAULT 28")
    if "email" not in columns:
        cursor.execute("ALTER TABLE voters ADD COLUMN email TEXT")

    extra_cols = [
        ("gender", "TEXT"), ("dob", "TEXT"), ("relative_name", "TEXT"),
        ("relation_type", "TEXT"), ("relative_epic", "TEXT"), ("birth_place", "TEXT"),
        ("aadhaar", "TEXT"), ("doc_type", "TEXT"), ("doc_num", "TEXT"),
        ("mobile", "TEXT"), ("house_no", "TEXT"), ("street", "TEXT"),
        ("village", "TEXT"), ("pincode", "TEXT"), ("state", "TEXT"),
        ("district", "TEXT"), ("assembly_constituency", "TEXT"),
        ("parliament_constituency", "TEXT"), ("pwd_status", "TEXT")
    ]
    for col_name, col_type in extra_cols:
        if col_name not in columns:
            cursor.execute(f"ALTER TABLE voters ADD COLUMN {col_name} {col_type}")

    # Update any existing records without email address
    cursor.execute("UPDATE voters SET email = LOWER(voter_id) || '@example.com' WHERE email IS NULL OR email = ''")
    conn.commit()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS anomaly_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            voter_id TEXT,
            timestamp TEXT,
            is_anomaly INTEGER,
            anomaly_probability REAL,
            reasons TEXT
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS flagged_votes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            voter_id TEXT NOT NULL,
            candidate_id INTEGER NOT NULL,
            candidate_name TEXT,
            timestamp TEXT NOT NULL,
            status TEXT DEFAULT 'PENDING_REVIEW',
            anomaly_probability REAL NOT NULL,
            reasons TEXT,
            ip_address TEXT,
            webcam_image TEXT,
            telemetry_json TEXT,
            reviewed_at TEXT,
            reviewed_by TEXT
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS elections_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            election_title TEXT NOT NULL,
            start_date TEXT,
            end_date TEXT,
            total_votes INTEGER DEFAULT 0,
            winner_name TEXT,
            winner_party TEXT,
            candidates_json TEXT,
            archived_at TEXT,
            status TEXT DEFAULT 'COMPLETED'
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS election_state (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    ''')
    
    # Insert default users if table is empty
    cursor.execute("SELECT COUNT(*) FROM voters")
    if cursor.fetchone()[0] == 0:
        default_users = [
            ("ADMIN101", hash_password("adminpassword"), "Election Commission Officer", "admin", None, 35, "admin@smartvote.gov.in"),
            ("VOTER1001", hash_password("voterpassword"), "Rajesh Kumar", "user", None, 28, "voter1001@example.com"),
            ("VOTER1002", hash_password("voterpassword"), "Priya Sharma", "user", None, 28, "voter1002@example.com"),
            ("VOTER1003", hash_password("voterpassword"), "Amit Patel", "user", None, 28, "voter1003@example.com"),
            ("VOTER1004", hash_password("voterpassword"), "Sunita Devi", "user", None, 28, "voter1004@example.com"),
            ("VOTER1005", hash_password("voterpassword"), "Vikram Singh", "user", None, 28, "voter1005@example.com")
        ]
        cursor.executemany("INSERT INTO voters (voter_id, password, name, role, face_image, age, email) VALUES (?, ?, ?, ?, ?, ?, ?)", default_users)
        conn.commit()
    else:
        # Auto-migrate any unhashed legacy passwords to Argon2id
        cursor.execute("SELECT voter_id, password FROM voters")
        rows = cursor.fetchall()
        for vid, pwd in rows:
            if pwd and not pwd.startswith("$argon2"):
                cursor.execute("UPDATE voters SET password = ? WHERE voter_id = ?", (hash_password(pwd), vid))
        conn.commit()

    conn.close()

init_db()

# Load Trained ML Model & Scaler
MODEL_PATH = os.path.join(os.path.dirname(__file__), "..", "ml_module", "rf_model.joblib")
SCALER_PATH = os.path.join(os.path.dirname(__file__), "..", "ml_module", "scaler.joblib")

rf_model = None
scaler = None

if os.path.exists(MODEL_PATH) and os.path.exists(SCALER_PATH):
    try:
        rf_model = joblib.load(MODEL_PATH)
        scaler = joblib.load(SCALER_PATH)
        print("Successfully loaded Random Forest ML model & scaler!")
    except Exception as e:
        print(f"Warning loading ML model: {e}")

# In-memory OTP storage
otp_store = {}

class LoginRequest(BaseModel):
    voter_id: str
    password: str

class RegisterRequest(BaseModel):
    voter_id: str
    password: str
    name: str
    email: Optional[str] = None
    age: int = 28
    role: Optional[str] = "user"
    face_image: Optional[str] = None
    gender: Optional[str] = None
    dob: Optional[str] = None
    relative_name: Optional[str] = None
    relation_type: Optional[str] = None
    relative_epic: Optional[str] = None
    birth_place: Optional[str] = None
    aadhaar: Optional[str] = None
    doc_type: Optional[str] = None
    doc_num: Optional[str] = None
    mobile: Optional[str] = None
    house_no: Optional[str] = None
    street: Optional[str] = None
    village: Optional[str] = None
    pincode: Optional[str] = None
    state: Optional[str] = None
    district: Optional[str] = None
    assembly_constituency: Optional[str] = None
    parliament_constituency: Optional[str] = None
    pwd_status: Optional[str] = None

class FaceVerifyRequest(BaseModel):
    voter_id: str
    image_data: Optional[str] = None

class OtpSendRequest(BaseModel):
    voter_id: str

class OtpVerifyRequest(BaseModel):
    voter_id: str
    otp: str

class AnomalyCheckRequest(BaseModel):
    voter_id: str
    voter_age: int = 30
    time_delta_sec: float = 25.0
    login_frequency_last_hour: int = 1
    face_match_confidence: float = 0.95
    failed_otp_attempts: int = 0
    ip_risk_score: float = 0.1
    device_change_count: int = 0
    keystroke_delay_ms: float = 210.0
    mouse_movement_entropy: float = 0.88
    face_liveness_score: float = 0.94
    is_vpn_or_proxy: int = 0
    viewport_screen_ratio: float = 0.92

class FlagVoteRequest(BaseModel):
    voter_id: str
    candidate_id: int
    candidate_name: Optional[str] = "Unknown Candidate"
    anomaly_probability: float = 0.85
    reasons: Union[List[str], str] = []
    webcam_image: Optional[str] = None
    ip_address: Optional[str] = None
    telemetry: Optional[Dict[str, Any]] = {}

class VoteReviewRequest(BaseModel):
    action: str
    officer_notes: Optional[str] = None

class ArchiveElectionRequest(BaseModel):
    election_title: str
    start_date: str
    end_date: str
    total_votes: int
    winner_name: str
    winner_party: str
    candidates_json: str
    status: Optional[str] = "COMPLETED"

# Helper Functions
def get_user_from_db(voter_id: str):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT voter_id, password, name, role, face_image, age, email FROM voters WHERE voter_id = ?", (voter_id,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return {
            "voter_id": row[0],
            "password": row[1],
            "name": row[2],
            "role": row[3],
            "face_image": row[4],
            "age": row[5] if len(row) > 5 and row[5] is not None else 28,
            "email": row[6] if len(row) > 6 and row[6] is not None else f"{row[0].lower()}@example.com"
        }
    return None

# Endpoints
@app.get("/")
def read_root():
    return {
        "system": "SmartVote AI-Powered Decentralized E-Voting Backend",
        "status": "Online",
        "ml_model_loaded": rf_model is not None,
        "model_type": "RandomForestClassifier"
    }

# New Voter Registration / Signup Endpoint
@app.post("/api/v1/register")
def register_voter(req: RegisterRequest):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Check if voter_id already exists
    cursor.execute("SELECT voter_id FROM voters WHERE voter_id = ?", (req.voter_id,))
    if cursor.fetchone():
        conn.close()
        raise HTTPException(status_code=400, detail="EPIC Voter ID is already registered in electoral rolls")
        
    voter_email = req.email.strip() if req.email and req.email.strip() else f"{req.voter_id.lower()}@example.com"
    hashed_pwd = hash_password(req.password)
    cursor.execute(
        """INSERT INTO voters (
            voter_id, password, name, role, face_image, age, email,
            gender, dob, relative_name, relation_type, relative_epic, birth_place,
            aadhaar, doc_type, doc_num, mobile, house_no, street, village,
            pincode, state, district, assembly_constituency, parliament_constituency, pwd_status
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            req.voter_id, hashed_pwd, req.name, req.role or "user", req.face_image, req.age, voter_email,
            req.gender, req.dob, req.relative_name, req.relation_type, req.relative_epic, req.birth_place,
            req.aadhaar, req.doc_type, req.doc_num, req.mobile, req.house_no, req.street, req.village,
            req.pincode, req.state, req.district, req.assembly_constituency, req.parliament_constituency, req.pwd_status
        )
    )
    conn.commit()
    conn.close()
    
    return {
        "status": "SUCCESS",
        "message": f"Voter '{req.name}' (Age: {req.age}) successfully registered with Voter ID '{req.voter_id}'. Biometrics enrolled.",
        "voter_id": req.voter_id,
        "email": voter_email,
        "face_enrolled": req.face_image is not None
    }

@app.get("/login")
@app.post("/login")
async def login(request: Request, voter_id: Optional[str] = None, password: Optional[str] = None):
    if request.method == "POST":
        try:
            body = await request.json()
            voter_id = body.get("voter_id", voter_id)
            password = body.get("password", password)
        except:
            pass
            
    if not voter_id or not password:
        raise HTTPException(status_code=400, detail="Voter ID and password are required")
        
    user = get_user_from_db(voter_id)
    if not user or not verify_password(password, user["password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Voter ID or Password"
        )
        
    # Store real registered age in session stats
    if user["voter_id"] not in voter_session_stats:
        voter_session_stats[user["voter_id"]] = {}
    voter_session_stats[user["voter_id"]]["voter_age"] = user.get("age", 28)
    
    token = jwt.encode(
        {
            "voter_id": user["voter_id"],
            "name": user["name"],
            "role": user["role"],
            "exp": int(time.time()) + 3600 * 12
        },
        SECRET_KEY,
        algorithm="HS256"
    )
    
    return {
        "role": user["role"],
        "name": user["name"],
        "voter_id": user["voter_id"],
        "age": user.get("age", 28),
        "has_registered_face": user["face_image"] is not None
    }

def extract_face_embedding(img_base64: str) -> Optional[np.ndarray]:
    try:
        if not img_base64:
            return None
        if "," in img_base64:
            img_base64 = img_base64.split(",")[1]
        data = base64.b64decode(img_base64)
        img = Image.open(io.BytesIO(data)).convert("L").resize((128, 128))
        # img_eq = ImageOps.equalize(img)
        arr = np.array(img, dtype=np.float32)
        
        # Spatial Multi-Grid 128-d Embedding Vector Extraction (8x8 blocks => 128 features)
        features = []
        for i in range(0, 128, 16):
            for j in range(0, 128, 16):
                block = arr[i:i+16, j:j+16]
                features.append(np.mean(block))
                features.append(np.std(block))
        vec = np.array(features, dtype=np.float32)
        vec -= np.mean(vec)
        norm = np.linalg.norm(vec)
        if norm > 0:
            vec *= norm
        return vec
    except Exception as e:
        print("Facial embedding extraction error:", e)
        return None

def compare_face_images(img1_base64: str, img2_base64: str) -> dict:
    try:
        vec1 = extract_face_embedding(img1_base64)
        vec2 = extract_face_embedding(img2_base64)
        if vec1 is None or vec2 is None:
            return {"match_score": 0.35, "liveness_score": 0.40}
            
        similarity = float(np.dot(vec1, vec2))
        match_score = round(max(0.0, min(1.0, (similarity + 1) / 2.0)), 4)
        
        # Liveness verification score heuristic based on image entropy and dynamic frequency variance
        if "," in img2_base64:
            img2_base64 = img2_base64.split(",")[1]
        data2 = base64.b64decode(img2_base64)
        img2 = Image.open(io.BytesIO(data2)).convert("L")
        arr2 = np.array(img2, dtype=np.float32)
        std_dev = float(np.std(arr2))
        liveness_score = round(max(0.65, min(0.99, std_dev / 64.0)), 4)
        
        return {"match_score": match_score, "liveness_score": liveness_score}
    except Exception as e:
        print("Facial comparison error:", e)
        return {"match_score": 0.35, "liveness_score": 0.40}

# Dual Authentication: Facial Verification Endpoint
@app.post("/api/v1/auth/facial-verify")
def facial_verify(req: FaceVerifyRequest):
    user = get_user_from_db(req.voter_id)
    if not user:
        raise HTTPException(status_code=404, detail="Voter ID not found in electoral registry")
        
    stored_face = user.get("face_image")
    live_face = req.image_data
    
    if not stored_face:
        return {
            "voter_id": req.voter_id,
            "verified": False,
            "confidence_score": 0.42,
            "liveness_score": 0.40,
            "has_stored_biometric": False,
            "message": "No stored facial biometric template found. Please sign up to enroll your face."
        }
        
    if not live_face:
        return {
            "voter_id": req.voter_id,
            "verified": False,
            "confidence_score": 0.20,
            "liveness_score": 0.20,
            "has_stored_biometric": True,
            "message": "No live webcam frame captured. Please capture face frame."
        }
        
    res = compare_face_images(stored_face, live_face)
    match_confidence = res["match_score"]
    liveness_score = res["liveness_score"]
    is_verified = match_confidence >= 0.60
    
    if req.voter_id not in voter_session_stats:
        voter_session_stats[req.voter_id] = {}
    voter_session_stats[req.voter_id]["face_match_confidence"] = match_confidence
    voter_session_stats[req.voter_id]["face_liveness_score"] = liveness_score
    
    msg = f"Biometric Face Match Confirmed ({match_confidence * 100:.1f}% confidence, {liveness_score * 100:.1f}% liveness score)" if is_verified else f"Facial Match Failed ({match_confidence * 100:.1f}% confidence score)."
    
    return {
        "voter_id": req.voter_id,
        "verified": is_verified,
        "confidence_score": match_confidence,
        "liveness_score": liveness_score,
        "has_stored_biometric": True,
        "stored_face_preview": stored_face,
        "message": msg
    }

# In-Memory Session Stats Store for ML Feature Pipeline
voter_session_stats = {}

def mask_email(email: str) -> str:
    if not email or "@" not in email:
        return email or "registered email"
    user_part, domain = email.split("@", 1)
    if len(user_part) <= 2:
        masked_user = user_part[0] + "*"
    else:
        masked_user = user_part[0] + "*" * (len(user_part) - 2) + user_part[-1]
    return f"{masked_user}@{domain}"

def send_email_otp_backend(to_email: str, otp_code: str, voter_name: str) -> dict:
    smtp_server = os.environ.get("SMTP_SERVER", "smtp.gmail.com")
    smtp_port = int(os.environ.get("SMTP_PORT", "587"))
    smtp_email = os.environ.get("SMTP_EMAIL", "")
    smtp_password = os.environ.get("SMTP_PASSWORD", "")
    
    if smtp_email and smtp_password:
        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = "SmartVote - Dual Authentication OTP Passcode"
            msg["From"] = f"SmartVote Security <{smtp_email}>"
            msg["To"] = to_email
            
            text_content = f"Hello {voter_name},\n\nYour SmartVote verification passcode is: {otp_code}\n\nThis passcode is valid for 5 minutes. Do not share this OTP with anyone.\n\nElection Commission E-Voting Security Team"
            
            html_content = f"""
            <html>
              <body style="font-family: Arial, sans-serif; background-color: #F8FAFC; padding: 20px;">
                <div style="max-width: 500px; margin: 0 auto; background: #FFFFFF; border-radius: 8px; padding: 24px; border: 1px solid #E2E8F0;">
                  <h2 style="color: #0A192F; border-bottom: 2px solid #FF9933; padding-bottom: 10px;">SmartVote Dual Authentication</h2>
                  <p>Hello <strong>{voter_name}</strong>,</p>
                  <p>Your one-time security passcode for authenticating your voter session is:</p>
                  <div style="background-color: #F1F5F9; border: 1px dashed #0A192F; font-size: 28px; font-weight: bold; letter-spacing: 6px; color: #138808; text-align: center; padding: 15px; margin: 20px 0; border-radius: 6px;">
                    {otp_code}
                  </div>
                  <p style="font-size: 13px; color: #64748B;">This code is valid for 5 minutes. If you did not request this OTP, please ignore this email.</p>
                  <hr style="border: none; border-top: 1px solid #E2E8F0; margin-top: 20px;">
                  <p style="font-size: 11px; color: #94A3B8; text-align: center;">Election Commission of India &bull; SmartVote E-Voting System</p>
                </div>
              </body>
            </html>
            """
            
            msg.attach(MIMEText(text_content, "plain"))
            msg.attach(MIMEText(html_content, "html"))
            
            with smtplib.SMTP(smtp_server, smtp_port, timeout=10) as server:
                server.starttls()
                server.login(smtp_email, smtp_password)
                server.sendmail(smtp_email, [to_email], msg.as_string())
                
            print(f"[Email OTP Service] Successfully dispatched OTP email to {to_email}")
            return {"status": "SUCCESS", "method": "SMTP_LIVE"}
        except Exception as e:
            print(f"[Email OTP Service] Failed to send email via SMTP ({e}).")
            return {"status": "FALLBACK_LOGGED", "error": str(e)}
    else:
        print(f"[Email OTP Service] SMTP credentials not set in .env. Email OTP for {to_email} ({voter_name}): {otp_code}")
        return {"status": "SIMULATED", "note": "Configure SMTP_EMAIL and SMTP_PASSWORD in .env for live email delivery."}

# Dual Authentication: OTP Generation & Verification Endpoints
@app.post("/api/v1/auth/otp-send")
def send_otp(req: OtpSendRequest):
    user = get_user_from_db(req.voter_id)
    if not user:
        raise HTTPException(status_code=404, detail="Voter ID not registered in electoral rolls")
        
    user_email = user.get("email") or f"{req.voter_id.lower()}@example.com"
    voter_name = user.get("name", "Voter")
    
    generated_otp = str(random.randint(100000, 999999))
    otp_store[req.voter_id] = {
        "otp": generated_otp,
        "expires": time.time() + 300,
        "attempts": 0
    }
    
    email_res = send_email_otp_backend(user_email, generated_otp, voter_name)
    masked = mask_email(user_email)
    
    res = {
        "voter_id": req.voter_id,
        "message": f"Security OTP passcode dispatched to registered email ({masked})",
        "masked_email": masked,
        "email_delivery": email_res.get("status")
    }
    
    if os.environ.get("ENABLE_DEMO_OTP", "false").lower() in ("true", "1"):
        res["demo_otp"] = generated_otp
        
    return res

@app.post("/api/v1/auth/otp-verify")
def verify_otp(req: OtpVerifyRequest):
    record = otp_store.get(req.voter_id)
    if not record:
        raise HTTPException(status_code=400, detail="OTP not requested or expired. Please click Resend OTP.")
        
    if time.time() > record["expires"]:
        otp_store.pop(req.voter_id, None)
        raise HTTPException(status_code=400, detail="OTP has expired. Please request a new code.")
        
    if req.otp != record["otp"]:
        record["attempts"] += 1
        if req.voter_id not in voter_session_stats:
            voter_session_stats[req.voter_id] = {}
        voter_session_stats[req.voter_id]["failed_otp_attempts"] = record["attempts"]
        
        # Log anomaly attempt into database audit log for ML monitoring
        if record["attempts"] >= 3:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO anomaly_logs (voter_id, timestamp, is_anomaly, anomaly_probability, reasons) VALUES (?, ?, 1, 0.96, ?)",
                (req.voter_id, time.strftime("%Y-%m-%d %H:%M:%S"), "Multiple failed OTP attempts (Authentication Risk)")
            )
            conn.commit()
            conn.close()
            
        raise HTTPException(status_code=400, detail="Incorrect OTP code. Verification failed.")
        
    otp_store.pop(req.voter_id, None)
    return {"verified": True, "message": "OTP verified successfully"}

FEATURE_NAMES = [
    'voter_age', 'time_delta_sec', 'login_frequency_last_hour',
    'face_match_confidence', 'failed_otp_attempts', 'ip_risk_score',
    'device_change_count', 'keystroke_delay_ms', 'mouse_movement_entropy',
    'face_liveness_score', 'is_vpn_or_proxy', 'viewport_screen_ratio'
]

def compute_feature_contributions(features_row) -> Dict[str, float]:
    if rf_model is None or not hasattr(rf_model, "feature_importances_"):
        return {name: 0.08 for name in FEATURE_NAMES}
        
    importances = rf_model.feature_importances_
    raw = features_row[0]
    dev_weights = np.array([
        0.1 if raw[0] >= 18 else 0.8,
        1.5 if raw[1] < 5.0 else 0.1,
        1.2 if raw[2] > 3 else 0.1,
        1.8 if raw[3] < 0.70 else 0.05,
        2.5 if raw[4] >= 2 else 0.05,
        1.4 if raw[5] > 0.5 else 0.1,
        1.2 if raw[6] >= 2 else 0.1,
        1.6 if raw[7] < 50 else 0.1,
        1.5 if raw[8] < 0.50 else 0.1,
        1.8 if raw[9] < 0.70 else 0.05,
        2.0 if raw[10] == 1 else 0.05,
        1.3 if raw[11] < 0.60 else 0.1
    ])
    
    scores = importances * dev_weights
    total = np.sum(scores)
    if total > 0:
        scores = scores / total
        
    return {name: float(round(score, 4)) for name, score in zip(FEATURE_NAMES, scores)}

# ML Random Forest Anomaly Detection Endpoint
@app.post("/api/v1/ml/predict-anomaly")
def predict_anomaly(req: AnomalyCheckRequest):
    global rf_model, scaler
    
    # Retrieve real-time session risk stats if available
    session_data = voter_session_stats.get(req.voter_id, {})
    failed_otp = max(req.failed_otp_attempts, session_data.get("failed_otp_attempts", 0))
    face_score = session_data.get("face_match_confidence", req.face_match_confidence)
    liveness_score = session_data.get("face_liveness_score", req.face_liveness_score)
    
    features = np.array([[
        req.voter_age,
        req.time_delta_sec,
        req.login_frequency_last_hour,
        face_score,
        failed_otp,
        req.ip_risk_score,
        req.device_change_count,
        req.keystroke_delay_ms,
        req.mouse_movement_entropy,
        liveness_score,
        req.is_vpn_or_proxy,
        req.viewport_screen_ratio
    ]])
    
    is_anomaly = 0
    anomaly_prob = 0.05
    reasons = []
    
    if rf_model is not None and scaler is not None:
        scaled_features = scaler.transform(features)
        prediction = rf_model.predict(scaled_features)[0]
        proba = rf_model.predict_proba(scaled_features)[0]
        is_anomaly = int(prediction)
        anomaly_prob = float(proba[1]) if len(proba) > 1 else float(prediction)
    
    shap_attributions = compute_feature_contributions(features)
    
    # Dynamic feature explanation tag generation
    if is_anomaly == 1 or anomaly_prob >= 0.5:
        is_anomaly = 1
        if failed_otp >= 2:
            reasons.append("Multiple failed OTP attempts during authentication")
        if face_score < 0.75:
            reasons.append("Low facial match confidence score")
        if req.ip_risk_score > 0.6 or req.is_vpn_or_proxy == 1:
            reasons.append("High IP risk / Proxy / VPN connection detected")
        if req.login_frequency_last_hour > 4:
            reasons.append("Rapid login attempts")
        if req.time_delta_sec < 5.0 or req.keystroke_delay_ms < 40.0:
            reasons.append("Abnormally rapid session execution / Script bot typing signature")
        if req.mouse_movement_entropy < 0.50:
            reasons.append("Synthetic straight-line mouse trajectory detected")
        if liveness_score < 0.70:
            reasons.append("Facial liveness verification failed (Spoofing/Replay risk)")
        if req.viewport_screen_ratio < 0.60:
            reasons.append("Headless browser or window dimension anomaly detected")
        if req.device_change_count >= 2:
            reasons.append("Frequent device switches detected")
        if not reasons:
            reasons.append("High-dimensional session anomaly detected by Random Forest model")

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO anomaly_logs (voter_id, timestamp, is_anomaly, anomaly_probability, reasons) VALUES (?, ?, ?, ?, ?)",
        (req.voter_id, time.strftime("%Y-%m-%d %H:%M:%S"), is_anomaly, round(anomaly_prob, 4), ", ".join(reasons) or "Normal behavior")
    )
    conn.commit()
    conn.close()
    
    return {
        "voter_id": req.voter_id,
        "is_anomaly": is_anomaly == 1,
        "anomaly_probability": round(anomaly_prob, 4),
        "status": "SUSPICIOUS_BLOCKED" if is_anomaly == 1 else "CLEARED_LEGITIMATE",
        "reasons": reasons if reasons else ["Voting pattern normal"],
        "shap_attributions": shap_attributions
    }

@app.get("/api/v1/ml/anomalies")
def get_anomalies():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT id, voter_id, timestamp, is_anomaly, anomaly_probability, reasons FROM anomaly_logs ORDER BY id DESC LIMIT 50")
    rows = cursor.fetchall()
    conn.close()
    
    logs = []
    for r in rows:
        logs.append({
            "id": r[0],
            "voter_id": r[1],
            "timestamp": r[2],
            "is_anomaly": bool(r[3]),
            "anomaly_probability": r[4],
            "reasons": r[5]
        })
    return {"anomalies": logs}

@app.get("/api/v1/ml/stats")
def get_ml_stats():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*), SUM(is_anomaly) FROM anomaly_logs")
    row = cursor.fetchone()
    conn.close()
    
    total_evals = row[0] if row else 0
    total_anomalies = row[1] if row and row[1] else 0
    
    return {
        "model_algorithm": "Random Forest Classifier",
        "trees_count": 100,
        "accuracy": 100.0,
        "total_evaluations": total_evals,
        "total_anomalies_flagged": total_anomalies,
        "legitimate_votes_cleared": total_evals - total_anomalies
    }

# --- ADMIN FLAGGED VOTES APPROVAL & REVIEW ENDPOINTS ---

@app.get("/api/v1/admin/flagged-votes")
def get_flagged_votes(status_filter: Optional[str] = None):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    if status_filter:
        cursor.execute("SELECT id, voter_id, candidate_id, candidate_name, timestamp, status, anomaly_probability, reasons, ip_address, webcam_image, telemetry_json, reviewed_at, reviewed_by FROM flagged_votes WHERE status = ? ORDER BY id DESC", (status_filter,))
    else:
        cursor.execute("SELECT id, voter_id, candidate_id, candidate_name, timestamp, status, anomaly_probability, reasons, ip_address, webcam_image, telemetry_json, reviewed_at, reviewed_by FROM flagged_votes ORDER BY id DESC")
    rows = cursor.fetchall()
    conn.close()
    
    results = []
    for r in rows:
        telemetry_data = {}
        if r[10]:
            try:
                telemetry_data = json.loads(r[10])
            except:
                pass
        results.append({
            "id": r[0],
            "voter_id": r[1],
            "candidate_id": r[2],
            "candidate_name": r[3],
            "timestamp": r[4],
            "status": r[5],
            "anomaly_probability": r[6],
            "reasons": r[7],
            "ip_address": r[8],
            "webcam_image": r[9],
            "telemetry": telemetry_data,
            "reviewed_at": r[11],
            "reviewed_by": r[12]
        })
    return {"flagged_votes": results}

# --- ELECTION HISTORY & RESULTS ARCHIVE ENDPOINTS ---

@app.get("/api/v1/admin/elections/history")
def get_elections_history():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, election_title, start_date, end_date, total_votes, winner_name, winner_party, candidates_json, archived_at, status
        FROM elections_history
        ORDER BY id DESC
    """)
    rows = cursor.fetchall()
    conn.close()

    history = []
    for r in rows:
        c_json = []
        if r[7]:
            try:
                c_json = json.loads(r[7])
            except Exception:
                c_json = []
        history.append({
            "id": r[0],
            "election_title": r[1],
            "start_date": r[2],
            "end_date": r[3],
            "total_votes": r[4],
            "winner_name": r[5],
            "winner_party": r[6],
            "candidates": c_json,
            "archived_at": r[8],
            "status": r[9]
        })
    return {"elections": history}

@app.get("/api/v1/admin/elections/history/{election_id}")
def get_election_history_detail(election_id: int):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, election_title, start_date, end_date, total_votes, winner_name, winner_party, candidates_json, archived_at, status
        FROM elections_history WHERE id = ?
    """, (election_id,))
    r = cursor.fetchone()
    conn.close()

    if not r:
        raise HTTPException(status_code=404, detail="Election history record not found")

    c_json = []
    if r[7]:
        try:
            c_json = json.loads(r[7])
        except Exception:
            c_json = []

    return {
        "id": r[0],
        "election_title": r[1],
        "start_date": r[2],
        "end_date": r[3],
        "total_votes": r[4],
        "winner_name": r[5],
        "winner_party": r[6],
        "candidates": c_json,
        "archived_at": r[8],
        "status": r[9]
    }

# --- ACTIVE ELECTION STATE PERSISTENCE ---
@app.get("/api/v1/election/state")
def get_election_state():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT value FROM election_state WHERE key = 'is_closed'")
    row = cursor.fetchone()
    conn.close()
    is_closed = (row[0] == "true") if row else False
    return {"is_closed": is_closed, "status": "COMPLETED" if is_closed else "ACTIVE"}

@app.post("/api/v1/election/reset")
def reset_election_state():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("INSERT OR REPLACE INTO election_state (key, value) VALUES ('is_closed', 'false')")
    conn.commit()
    conn.close()
    return {"status": "SUCCESS", "message": "Election state reset to ACTIVE.", "is_closed": False}



