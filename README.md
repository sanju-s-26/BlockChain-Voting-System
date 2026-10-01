# Decentralized Voting System

A secure and transparent voting application built using Ethereum Blockchain, Node.js, FastAPI, and MySQL.

---

## Prerequisites

Ensure you have the following installed:
- **Node.js** (v18+)
- **Python** (v3.9+)
- **MySQL Server** (port 3306)
- **Ganache** (Local Ethereum Blockchain)
- **MetaMask** Extension for browser

---

## Setup Instructions

### 1. Database Setup
Create the MySQL database and required table:

```sql
CREATE DATABASE voter_db;
USE voter_db;

CREATE TABLE voters (
    voter_id VARCHAR(36) PRIMARY KEY NOT NULL,
    role ENUM('admin', 'user') NOT NULL,
    password VARCHAR(255) NOT NULL
);
```

Update your database credentials in `./Database_API/.env`:
```env
DB_HOST=localhost
DB_USER=root
DB_PASSWORD=your_password
DB_NAME=voter_db
```

---

### 2. Dependency Installation

**Node.js Dependencies:**
```bash
npm install
```

**Python Dependencies:**
```bash
pip install fastapi mysql-connector-python pydantic python-dotenv uvicorn PyJWT
```

---

### 3. Blockchain Setup

1. Start **Ganache** on `http://127.0.0.1:7545`.
2. Connect **MetaMask** to local network (`RPC URL: http://127.0.0.1:7545`, `Chain ID: 1337`).
3. Compile and migrate smart contracts:
   ```bash
   npx truffle compile
   npx truffle migrate
   ```

---

### 4. Running the Application

1. **Start the Database API Server:**
   ```bash
   cd Database_API
   uvicorn main:app --reload --host 127.0.0.1
   ```

2. **Build bundle & start Node web server (in root directory):**
   ```bash
   npx browserify ./src/js/app.js -o ./src/dist/app.bundle.js
   node index.js
   ```

3. Access the application in your browser at `http://localhost:8080`.
