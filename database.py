import os
import hashlib
import aiosqlite

DB_PATH = os.getenv("DB_PATH", "verification.db")

def hash_email(email: str) -> str:
    """Computes a salted SHA-256 hash of the normalized email address."""
    salt = os.getenv("EMAIL_SALT", "default-dev-salt-2026")
    normalized = email.strip().lower()
    return hashlib.sha256(f"{normalized}:{salt}".encode("utf-8")).hexdigest()

async def init_db() -> None:
    """Initializes the database schema."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS verified_users (
                discord_id INTEGER PRIMARY KEY,
                email_hash TEXT UNIQUE NOT NULL,
                verified_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS pending_otps (
                discord_id INTEGER PRIMARY KEY,
                email_hash TEXT NOT NULL,
                otp_code TEXT NOT NULL,
                expires_at REAL NOT NULL,
                attempts INTEGER DEFAULT 0
            )
        """)
        await db.commit()

async def check_existing_verification(discord_id: int, email_hash: str) -> tuple[bool, str]:
    """Checks if the Discord account or email hash is already registered."""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT 1 FROM verified_users WHERE discord_id = ?", (discord_id,)) as cur:
            if await cur.fetchone():
                return True, "Your Discord account is already verified."

        async with db.execute("SELECT 1 FROM verified_users WHERE email_hash = ?", (email_hash,)) as cur:
            if await cur.fetchone():
                return True, "This university account is already linked to another Discord user."

    return False, ""

async def store_otp(discord_id: int, email_hash: str, otp_code: str, expires_at: float) -> None:
    """Stores or updates a pending verification code."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT OR REPLACE INTO pending_otps (discord_id, email_hash, otp_code, expires_at, attempts)
            VALUES (?, ?, ?, ?, 0)
        """, (discord_id, email_hash, otp_code, expires_at))
        await db.commit()

async def validate_otp(discord_id: int, input_code: str, current_time: float) -> tuple[bool, str]:
    """Validates the submitted OTP against expiration, attempt limits, and hash matching."""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("""
            SELECT email_hash, otp_code, expires_at, attempts
            FROM pending_otps WHERE discord_id = ?
        """, (discord_id,)) as cur:
            row = await cur.fetchone()

        if not row:
            return False, "No active verification request found. Run `/verify` first."

        email_hash, otp_code, expires_at, attempts = row

        if current_time > expires_at:
            await db.execute("DELETE FROM pending_otps WHERE discord_id = ?", (discord_id,))
            await db.commit()
            return False, "Verification code expired. Request a new one using `/verify`."

        if attempts >= 3:
            await db.execute("DELETE FROM pending_otps WHERE discord_id = ?", (discord_id,))
            await db.commit()
            return False, "Too many failed attempts. Code invalidated. Request a new one."

        if input_code.strip() != otp_code:
            await db.execute("UPDATE pending_otps SET attempts = attempts + 1 WHERE discord_id = ?", (discord_id,))
            await db.commit()
            return False, f"Incorrect code. You have {2 - attempts} attempt(s) remaining."

        # Success: commit verified user and clean up pending OTP table
        await db.execute("INSERT INTO verified_users (discord_id, email_hash) VALUES (?, ?)", (discord_id, email_hash))
        await db.execute("DELETE FROM pending_otps WHERE discord_id = ?", (discord_id,))
        await db.commit()
        return True, "Verification successful."