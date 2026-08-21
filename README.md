# University Identity Verification & Access Control Bot

An asynchronous Discord automation and access-provisioning service engineered to secure student communities and streamline organizational onboarding. The bot enforces campus domain restrictions by pairing ephemeral Discord slash commands with cryptographically secure, time-limited one-time-password (OTP) verification sent to official student email addresses.

---

## Key Features

* **Ephemeral Slash Commands (`/verify`, `/confirm`):** Keeps student identifiers, NinerNET IDs, and OTP submission interactions private from public channel logs.
* **CSPRNG OTP Generation:** Generates cryptographically secure 6-digit verification codes using `secrets.randbelow` with a 10-minute Time-To-Live (TTL) expiration window.
* **Privacy-Preserving Salted Hashing:** Protects student identity data by storing salted SHA-256 hashes of email addresses rather than plaintext emails.
* **Anti-Abuse & Rate Limiting:** Enforces maximum verification attempt limits (3 strikes before token invalidation) and restricts single email association to one Discord user account.
* **Asynchronous Non-Blocking I/O:** Built entirely on asynchronous primitives (`discord.py`, `aiosqlite`, and `aiosmtplib` over SSL/TLS) for high concurrency and low latency.
* **Automated Role Elevation:** Instantly assigns the designated verified guild role upon successful token confirmation.

---

## System Architecture & Workflow

```text
[ Discord User ] 
       │
       ▼  1. /verify username:<id>
[ Discord Bot ] ──► Compute Salted SHA-256 Hash & Check Duplicate DB
       │
       ▼  2. Generate 6-Digit CSPRNG Token & Store Pending State
[ aiosmtplib ] ──► Send Email via TLS (Port 465) ──► [ Student Inbox ]
       │
       ▼  3. /confirm code:<123456>
[ Discord Bot ] ──► Validate Token, Expiration, & Attempt Limit
       │
       ▼  4. Verification Success
[ Discord Guild ] ──► Grant Verified Role + Persist in SQLite
```

---

## Tech Stack

* **Language:** Python 3.10+
* **Framework:** `discord.py` (App Commands / Interactions)
* **Database:** `aiosqlite` (Async SQLite3)
* **Mail Transport:** `aiosmtplib` (Direct SSL/TLS)
* **Security & Crypto:** Standard Library `hashlib`, `secrets`

---

## Project Structure

```text
discord-verification-bot/
├── .env.example
├── .gitignore
├── README.md
├── requirements.txt
├── bot.py          # Discord client setup, slash command routing, role management
├── database.py     # SQLite async schema, salted SHA-256 hashing, state validation
└── mailer.py       # Async SMTP message dispatch with TLS
```

---

## Getting Started

### 1. Prerequisites
* Python 3.10 or higher
* A registered Discord Bot Application with **Server Members Intent** enabled via the [Discord Developer Portal](https://discord.com/developers/applications).
* SMTP credentials (e.g., a Google App Password for Gmail/Google Workspace).

### 2. Installation & Environment Setup

Clone the repository and create a virtual environment:

```bash
git clone https://github.com/<your-username>/discord-verification-bot.git
cd discord-verification-bot

# Create and activate virtual environment
python -m venv .venv
# On Windows: .venv\Scripts\activate
# On macOS/Linux: source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Environment Configuration

Create a `.env` file in the root directory and configure the following variables:

```env
DISCORD_TOKEN=your_discord_bot_token
GUILD_ID=your_discord_server_id
VERIFIED_ROLE_ID=your_verified_role_id

# University Domain & Hashing Salt
ALLOWED_DOMAIN=charlotte.edu
EMAIL_SALT=your_custom_cryptographic_salt_string

# SMTP Configuration
SMTP_HOST=smtp.gmail.com
SMTP_PORT=465
SMTP_USER=your_organization_email@gmail.com
SMTP_PASS=your_16_character_app_password
EMAIL_FROM=your_organization_email@gmail.com
```

### 4. Role Hierarchy Requirement

To allow the bot to assign roles:
1. Navigate to **Server Settings → Roles** in your Discord server.
2. Ensure the bot's managed integration role is dragged **above** the verified member role in the hierarchy list.

### 5. Running the Bot

```bash
python bot.py
```

---

## Slash Commands

| Command | Arguments | Description |
| :--- | :--- | :--- |
| `/verify` | `username` (string) | Validates username syntax, calculates salted hash, generates OTP, and dispatches email. |
| `/confirm` | `code` (string) | Verifies the 6-digit OTP, updates database state, and assigns the verified role. |

---

## Database Schema

```sql
CREATE TABLE IF NOT EXISTS verified_users (
    discord_id INTEGER PRIMARY KEY,
    email_hash TEXT UNIQUE NOT NULL,
    verified_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS pending_otps (
    discord_id INTEGER PRIMARY KEY,
    email_hash TEXT NOT NULL,
    otp_code TEXT NOT NULL,
    expires_at REAL NOT NULL,
    attempts INTEGER DEFAULT 0
);
```

---
