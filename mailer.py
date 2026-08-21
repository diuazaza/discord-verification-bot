import os
from email.message import EmailMessage
import aiosmtplib
from dotenv import load_dotenv

load_dotenv()

SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", 465))
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASS = os.getenv("SMTP_PASS")
EMAIL_FROM = os.getenv("EMAIL_FROM", SMTP_USER)

async def send_otp_email(recipient_email: str, otp_code: str) -> None:
    """Dispatches a one-time verification passcode over asynchronous SMTP using direct SSL/TLS."""
    msg = EmailMessage()
    msg["From"] = EMAIL_FROM
    msg["To"] = recipient_email
    msg["Subject"] = "Your Community Verification Passcode"

    msg.set_content(
        f"Your verification code is: {otp_code}\n\n"
        f"This code will expire in 10 minutes.\n"
        f"Return to Discord and submit: /confirm code:{otp_code}\n\n"
        f"If you did not request this verification, please disregard this email."
    )

    await aiosmtplib.send(
        msg,
        hostname=SMTP_HOST,
        port=SMTP_PORT,
        username=SMTP_USER,
        password=SMTP_PASS,
        use_tls=True
    )