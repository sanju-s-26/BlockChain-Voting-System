let currentRole = 'user';
let pendingVoterId = '';
let pendingPassword = '';
let pendingToken = '';
let capturedSignupFaceBase64 = null;
let signupMediaStream = null;
let verifyMediaStream = null;

const API_BASE = 'http://127.0.0.1:8001';

window.generateAutoVoterId = function() {
  const randomNum = Math.floor(10000 + Math.random() * 90000);
  const generatedId = `VOTER-${randomNum}`;
  const regIdInput = document.getElementById('reg-id');
  if (regIdInput) regIdInput.value = generatedId;
  return generatedId;
};

window.switchTab = function(tabName) {
  const voterTab = document.getElementById('voterTabBtn');
  const signupTab = document.getElementById('signupTabBtn');
  const adminTab = document.getElementById('adminTabBtn');
  
  const loginForm = document.getElementById('loginForm');
  const signupForm = document.getElementById('signupForm');
  const idLabel = document.getElementById('idLabel');
  const voterInput = document.getElementById('voter-id');
  const loginSubmitBtn = document.getElementById('loginSubmitBtn');

  voterTab.classList.remove('active');
  signupTab.classList.remove('active');
  adminTab.classList.remove('active');

  loginForm.style.display = 'none';
  signupForm.style.display = 'none';

  if (tabName === 'signup') {
    signupTab.classList.add('active');
    signupForm.style.display = 'block';
    window.generateAutoVoterId();
    if (loginSubmitBtn) {
      loginSubmitBtn.innerHTML = '<i class="fa-solid fa-right-to-bracket"></i> Proceed to Dual Authentication';
    }
  } else if (tabName === 'admin') {
    currentRole = 'admin';
    adminTab.classList.add('active');
    loginForm.style.display = 'block';
    idLabel.innerText = 'Officer Registration ID / Badge Number';
    voterInput.placeholder = 'e.g. ADMIN101';
    if (loginSubmitBtn) {
      loginSubmitBtn.innerHTML = '<i class="fa-solid fa-right-to-bracket"></i> Login';
    }
  } else {
    currentRole = 'user';
    voterTab.classList.add('active');
    loginForm.style.display = 'block';
    idLabel.innerText = 'EPIC Voter ID / Registration Number';
    voterInput.placeholder = 'e.g. VOTER1001';
    if (loginSubmitBtn) {
      loginSubmitBtn.innerHTML = '<i class="fa-solid fa-right-to-bracket"></i> Proceed to Dual Authentication';
    }
  }
};

window.generateCaptcha = function() {
  const chars = '23456789ABCDEFGHJKLMNPQRSTUVWXYZ';
  let captcha = '';
  for (let i = 0; i < 5; i++) {
    captcha += chars.charAt(Math.floor(Math.random() * chars.length));
  }
  const captchaElem = document.getElementById('captchaCode');
  if (captchaElem) captchaElem.innerText = captcha;
};

window.adjustFontSize = function(delta) {
  const current = parseFloat(getComputedStyle(document.body).fontSize);
  document.body.style.fontSize = (current + delta * 1) + 'px';
};

window.toggleContrast = function() {
  document.body.classList.toggle('high-contrast');
};

window.closeModal = function(id) {
  const elem = document.getElementById(id);
  if (elem) elem.style.display = 'none';
  if (verifyMediaStream) {
    verifyMediaStream.getTracks().forEach(track => track.stop());
    verifyMediaStream = null;
  }
};

/* --- FACIAL ENROLLMENT FOR SIGNUP --- */
window.startSignupWebcam = async function() {
  const video = document.getElementById('signupVideo');
  const preview = document.getElementById('signupFacePreview');
  try {
    signupMediaStream = await navigator.mediaDevices.getUserMedia({ video: true });
    video.srcObject = signupMediaStream;
    video.style.display = 'block';
    preview.style.display = 'none';
  } catch (err) {
    // If real webcam denied or unattached, generate synthetic face matrix canvas for demo
    createSyntheticFaceCanvas('signupCanvas');
    const canvas = document.getElementById('signupCanvas');
    capturedSignupFaceBase64 = canvas.toDataURL('image/png');
    preview.innerHTML = `<img src="${capturedSignupFaceBase64}" style="width: 100px; height: 100px; border-radius: 50%; border: 3px solid #138808; object-fit: cover;"/><p style="color: #138808; font-weight: 600; margin-top: 6px;">Facial Biometric Enrolled (Simulated)</p>`;
    preview.style.display = 'block';
    video.style.display = 'none';
  }
};

window.snapSignupFace = function() {
  const video = document.getElementById('signupVideo');
  const canvas = document.getElementById('signupCanvas');
  const preview = document.getElementById('signupFacePreview');

  if (signupMediaStream && video.srcObject) {
    canvas.width = video.videoWidth || 320;
    canvas.height = video.videoHeight || 240;
    const ctx = canvas.getContext('2d');
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
    capturedSignupFaceBase64 = canvas.toDataURL('image/png');
    
    // Stop camera stream
    signupMediaStream.getTracks().forEach(t => t.stop());
    signupMediaStream = null;
    video.style.display = 'none';

    preview.innerHTML = `<img src="${capturedSignupFaceBase64}" style="width: 100px; height: 100px; border-radius: 50%; border: 3px solid #138808; object-fit: cover;"/><p style="color: #138808; font-weight: 600; margin-top: 6px;">Facial Biometric Photo Enrolled!</p>`;
    preview.style.display = 'block';
  } else {
    // Fallback snap
    createSyntheticFaceCanvas('signupCanvas');
    capturedSignupFaceBase64 = canvas.toDataURL('image/png');
    preview.innerHTML = `<img src="${capturedSignupFaceBase64}" style="width: 100px; height: 100px; border-radius: 50%; border: 3px solid #138808; object-fit: cover;"/><p style="color: #138808; font-weight: 600; margin-top: 6px;">Facial Biometric Photo Enrolled!</p>`;
    preview.style.display = 'block';
  }
};

function createSyntheticFaceCanvas(canvasId) {
  const canvas = document.getElementById(canvasId);
  canvas.width = 200;
  canvas.height = 200;
  const ctx = canvas.getContext('2d');
  ctx.fillStyle = '#0A192F';
  ctx.fillRect(0, 0, 200, 200);
  ctx.fillStyle = '#FF9933';
  ctx.beginPath(); ctx.arc(100, 80, 45, 0, Math.PI * 2); ctx.fill();
  ctx.fillStyle = '#138808';
  ctx.beginPath(); ctx.arc(100, 180, 70, 0, Math.PI * 2); ctx.fill();
  ctx.fillStyle = '#FFFFFF';
  ctx.beginPath(); ctx.arc(85, 75, 6, 0, Math.PI * 2); ctx.fill();
  ctx.beginPath(); ctx.arc(115, 75, 6, 0, Math.PI * 2); ctx.fill();
}

document.addEventListener('DOMContentLoaded', () => {
  generateCaptcha();

  // LOGIN FORM SUBMISSION
  const loginForm = document.getElementById('loginForm');
  if (loginForm) {
    loginForm.addEventListener('submit', async (event) => {
      event.preventDefault();

      const voter_id = document.getElementById('voter-id').value.trim();
      const password = document.getElementById('password').value.trim();
      const captchaInput = document.getElementById('captchaInput').value.trim().toUpperCase();
      const captchaCode = document.getElementById('captchaCode').innerText.trim().toUpperCase();
      const errBox = document.getElementById('loginError');

      errBox.style.display = 'none';

      if (captchaInput !== captchaCode) {
        errBox.innerText = 'Security Verification code mismatch. Please try again.';
        errBox.style.display = 'block';
        generateCaptcha();
        return;
      }

      try {
        const response = await fetch(`${API_BASE}/login`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({ voter_id, password })
        });

        if (!response.ok) {
          const errData = await response.json().catch(() => ({}));
          throw new Error(errData.detail || 'Invalid Voter ID or Password');
        }

        const data = await response.json();
        pendingVoterId = data.voter_id || voter_id;
        pendingPassword = password;
        pendingToken = data.token;

        // Session Telemetry Initialization for ML Anomaly Pipeline
        localStorage.setItem('loginStartTime', Date.now().toString());
        localStorage.setItem('voterAge', (data.age || 28).toString());

        const currentFP = btoa(navigator.userAgent + '_' + screen.width + 'x' + screen.height);
        const knownFP = localStorage.getItem('deviceFingerprint');
        let deviceChangeCount = parseInt(localStorage.getItem('deviceChangeCount') || '0', 10);
        if (knownFP && knownFP !== currentFP) {
          deviceChangeCount += 1;
        }
        localStorage.setItem('deviceFingerprint', currentFP);
        localStorage.setItem('deviceChangeCount', deviceChangeCount.toString());

        const now = Date.now();
        let loginHistory = JSON.parse(localStorage.getItem('loginHistory') || '[]');
        loginHistory = loginHistory.filter(ts => now - ts < 3600000);
        loginHistory.push(now);
        localStorage.setItem('loginHistory', JSON.stringify(loginHistory));

        if (data.role === 'admin') {
          localStorage.setItem('jwtTokenAdmin', data.token);
          localStorage.setItem('voterName', data.name || 'Election Officer');
          window.location.replace(`http://127.0.0.1:8080/admin.html?Authorization=Bearer ${data.token}`);
        } else {
          document.getElementById('facialModal').style.display = 'flex';
          resetFacialModal();
        }
      } catch (err) {
        errBox.innerText = err.message || 'Login failed. Please check your credentials.';
        errBox.style.display = 'block';
      }
    });
  }

  // SIGNUP FORM SUBMISSION
  const signupForm = document.getElementById('signupForm');
  if (signupForm) {
    signupForm.addEventListener('submit', async (event) => {
      event.preventDefault();

      const name = (document.getElementById('reg-name')?.value || 'Citizen').trim();
      const ageVal = document.getElementById('reg-age')?.value.trim();
      const age = parseInt(ageVal, 10) || 28;
      const voter_id = (document.getElementById('reg-id')?.value || generateAutoVoterId()).trim();
      const password = (document.getElementById('reg-password')?.value || 'Voter@123').trim();
      
      // Extract Optional ECI Form 6 Fields
      const gender = document.getElementById('reg-gender')?.value || '';
      const dob = document.getElementById('reg-dob')?.value || '';
      const relative_name = document.getElementById('reg-relative-name')?.value || '';
      const relation_type = document.getElementById('reg-relation-type')?.value || '';
      const relative_epic = document.getElementById('reg-relative-epic')?.value || '';
      const birth_place = document.getElementById('reg-birth-place')?.value || '';
      const aadhaar = document.getElementById('reg-aadhaar')?.value || '';
      const doc_type = document.getElementById('reg-doc-type')?.value || '';
      const doc_num = document.getElementById('reg-doc-num')?.value || '';
      const mobile = document.getElementById('reg-mobile')?.value || '';
      const email = document.getElementById('reg-email')?.value || '';
      const house_no = document.getElementById('reg-house-no')?.value || '';
      const street = document.getElementById('reg-street')?.value || '';
      const village = document.getElementById('reg-village')?.value || '';
      const pincode = document.getElementById('reg-pincode')?.value || '';
      const state = document.getElementById('reg-state')?.value || '';
      const district = document.getElementById('reg-district')?.value || '';
      const assembly_constituency = document.getElementById('reg-assembly-constituency')?.value || '';
      const parliament_constituency = document.getElementById('reg-parliament-constituency')?.value || '';
      const pwd_status = document.getElementById('reg-pwd-status')?.value || 'None';

      const msgDiv = document.getElementById('signupMsg');
      if (msgDiv) msgDiv.style.display = 'none';

      if (!capturedSignupFaceBase64) {
        // Auto capture synthetic snapshot if omitted
        snapSignupFace();
      }

      // Save optional voter profile data locally for session usage
      const voterProfile = {
        voter_id, name, age, gender, dob, relative_name, relation_type, relative_epic,
        birth_place, aadhaar, doc_type, doc_num, mobile, email, house_no, street,
        village, pincode, state, district, assembly_constituency, parliament_constituency, pwd_status
      };
      localStorage.setItem(`voter_profile_${voter_id}`, JSON.stringify(voterProfile));

      try {
        const response = await fetch(`${API_BASE}/api/v1/register`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            voter_id,
            password,
            name,
            age,
            role: 'user',
            face_image: capturedSignupFaceBase64,
            ...voterProfile
          })
        });

        const data = await response.json();
        if (!response.ok) {
          throw new Error(data.detail || 'Registration failed');
        }

        msgDiv.className = 'alert alert-info';
        msgDiv.innerHTML = `<i class="fa-solid fa-circle-check"></i> ${data.message}`;
        msgDiv.style.display = 'block';

        setTimeout(() => {
          switchTab('voter');
          document.getElementById('voter-id').value = voter_id;
          document.getElementById('password').value = password;
        }, 2000);

      } catch (err) {
        msgDiv.className = 'alert alert-danger';
        msgDiv.innerText = err.message || 'Registration completed successfully (Demo Mode).';
        msgDiv.style.display = 'block';

        // Graceful fallback for demo UI if local backend server is not running
        setTimeout(() => {
          switchTab('voter');
          const voterInput = document.getElementById('voter-id');
          const passInput = document.getElementById('password');
          if (voterInput) voterInput.value = voter_id;
          if (passInput) passInput.value = password;
        }, 2000);
      }
    });
  }
});

function resetFacialModal() {
  document.getElementById('scannerStatus').innerHTML = '<i class="fa-solid fa-camera"></i> Ready for Facial Scan...';
  document.getElementById('startScanBtn').disabled = false;
  document.getElementById('matchScoreContainer').style.display = 'none';
  document.getElementById('progressBar').style.width = '0%';
  
  // Try to start live verify camera
  const video = document.getElementById('loginVerifyVideo');
  const avatar = document.getElementById('faceAvatarIcon');
  navigator.mediaDevices.getUserMedia({ video: true }).then(stream => {
    verifyMediaStream = stream;
    video.srcObject = stream;
    video.style.display = 'block';
    avatar.style.display = 'none';
  }).catch(() => {
    video.style.display = 'none';
    avatar.style.display = 'block';
  });
}

window.runFacialScan = async function() {
  const startBtn = document.getElementById('startScanBtn');
  const statusDiv = document.getElementById('scannerStatus');
  const matchContainer = document.getElementById('matchScoreContainer');
  const progressBar = document.getElementById('progressBar');
  const scoreVal = document.getElementById('scoreVal');
  const video = document.getElementById('loginVerifyVideo');
  const canvas = document.getElementById('loginVerifyCanvas');

  startBtn.disabled = true;
  statusDiv.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Comparing live webcam frame against registered biometric face in voters.db...';

  // Capture frame from webcam if video is active
  let liveFrameBase64 = null;
  if (video && video.srcObject && video.videoWidth > 0) {
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    const ctx = canvas.getContext('2d');
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
    liveFrameBase64 = canvas.toDataURL('image/jpeg', 0.8);
  }

  try {
    const response = await fetch(`${API_BASE}/api/v1/auth/facial-verify`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        voter_id: pendingVoterId,
        image_data: liveFrameBase64
      })
    });
    const result = await response.json();

    const confidencePct = (result.confidence_score * 100).toFixed(1);
    matchContainer.style.display = 'block';
    progressBar.style.width = `${confidencePct}%`;
    scoreVal.innerText = `${confidencePct}%`;

    // Telemetry: store real face match score & liveness score for ML pipeline
    localStorage.setItem('faceMatchConfidence', (result.confidence_score || 0.95).toString());
    localStorage.setItem('faceLivenessScore', (result.liveness_score || 0.94).toString());

    if (result.verified) {
      progressBar.style.backgroundColor = '#10B981';
      statusDiv.innerHTML = `<span class="text-success"><i class="fa-solid fa-circle-check"></i> ${result.message}</span>`;
      setTimeout(() => {
        document.getElementById('facialModal').style.display = 'none';
        triggerOtpModal();
      }, 1500);
    } else {
      progressBar.style.backgroundColor = '#EF4444';
      statusDiv.innerHTML = `<span class="text-danger" style="color: #EF4444; font-weight: 600;"><i class="fa-solid fa-circle-xmark"></i> ${result.message}</span>`;
      startBtn.disabled = false;
      startBtn.innerHTML = '<i class="fa-solid fa-rotate-right"></i> Retry Facial Verification';
    }
  } catch (err) {
    statusDiv.innerHTML = `<span class="text-danger">Verification service error: ${err.message}</span>`;
    startBtn.disabled = false;
  }
};

async function triggerOtpModal() {
  document.getElementById('otpModal').style.display = 'flex';
  document.getElementById('otpError').style.display = 'none';
  const demoBox = document.getElementById('demoOtpAlert');
  if (demoBox) demoBox.style.display = 'none';
  
  try {
    const response = await fetch(`${API_BASE}/api/v1/auth/otp-send`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ voter_id: pendingVoterId })
    });
    const data = await response.json();
    
    const descElem = document.getElementById('otpModalDesc');
    if (descElem && data.masked_email) {
      descElem.innerHTML = `<i class="fa-solid fa-envelope"></i> A time-sensitive One-Time Password (OTP) has been sent to your registered email: <strong>${data.masked_email}</strong>.`;
    }
    
    if (data.demo_otp && demoBox) {
      document.getElementById('demoOtpValue').innerText = data.demo_otp;
      demoBox.style.display = 'block';
    }
  } catch (e) {
    console.error("Error triggering OTP:", e);
  }
}

window.resendOtp = function() {
  triggerOtpModal();
};

window.verifyOtpCode = async function() {
  const otp = document.getElementById('otpInput').value.trim();
  const errDiv = document.getElementById('otpError');
  errDiv.style.display = 'none';

  if (!otp || otp.length < 6) {
    errDiv.innerText = 'Please enter a valid 6-digit OTP code.';
    errDiv.style.display = 'block';
    return;
  }

  try {
    const response = await fetch(`${API_BASE}/api/v1/auth/otp-verify`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ voter_id: pendingVoterId, otp })
    });

    if (!response.ok) {
      // Record telemetry for failed attempt
      const currentFailed = parseInt(localStorage.getItem('failedOtpAttempts') || '0', 10);
      localStorage.setItem('failedOtpAttempts', (currentFailed + 1).toString());
      const errData = await response.json().catch(() => ({}));
      throw new Error(errData.detail || 'OTP verification failed');
    }

    localStorage.setItem('jwtTokenVoter', pendingToken);
    localStorage.setItem('voterId', pendingVoterId);
    window.location.replace(`http://127.0.0.1:8080/index.html?Authorization=Bearer ${pendingToken}`);

  } catch (err) {
    errDiv.innerText = err.message || 'Incorrect OTP code. Please try again.';
    errDiv.style.display = 'block';
  }
};
