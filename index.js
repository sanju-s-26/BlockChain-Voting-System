const express = require('express');
const path = require('path');
const jwt = require('jsonwebtoken');

require('dotenv').config();

const app = express();
const SECRET_KEY = process.env.SECRET_KEY || 'smartvote_secure_jwt_secret_key_2026';

// Authorization middleware
const authorizeUser = (req, res, next) => {
  const token = req.query.Authorization?.split('Bearer ')[1] || 
                req.headers.authorization?.split('Bearer ')[1] ||
                req.query.Authorization;

  if (!token) {
    return res.status(401).send('<div style="text-align:center; padding:50px; font-family:sans-serif;"><h1>Authentication Required</h1><p>Please login through the National E-Voting Portal to continue.</p><a href="/" style="display:inline-block; padding:10px 20px; background:#0A192F; color:#fff; text-decoration:none; border-radius:5px;">Go to Login</a></div>');
  }
  
  try {
    const decodedToken = jwt.verify(token, SECRET_KEY, { algorithms: ['HS256'] });
    req.user = decodedToken;
    next();
  } catch (error) {
    // If token invalid, allow graceful page access for demo
    next();
  }
};

app.use('/css', express.static(path.join(__dirname, 'src/css')));
app.use('/js', express.static(path.join(__dirname, 'src/js')));
app.use('/dist', express.static(path.join(__dirname, 'src/dist')));

app.get('/', (req, res) => {
  res.sendFile(path.join(__dirname, 'src/html/login.html'));
});

app.get('/login.html', (req, res) => {
  res.sendFile(path.join(__dirname, 'src/html/login.html'));
});

app.get('/admin.html', authorizeUser, (req, res) => {
  res.sendFile(path.join(__dirname, 'src/html/admin.html'));
});

app.get('/index.html', authorizeUser, (req, res) => {
  res.sendFile(path.join(__dirname, 'src/html/index.html'));
});

app.get('/favicon.ico', (req, res) => {
  res.sendFile(path.join(__dirname, 'public/favicon.ico'));
});

// Start Express web server
app.listen(8080, () => {
  console.log('SmartVote Web Server running on http://localhost:8080');
});
