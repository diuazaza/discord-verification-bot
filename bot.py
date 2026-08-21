import os
import re
import secrets
import time
import discord
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv

import database as db
import mailer

load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
GUILD_ID = int(os.getenv("GUILD_ID", 0))
VERIFIED_ROLE_ID = int(os.getenv("VERIFIED_ROLE_ID", 0))
ALLOWED_DOMAIN = os.getenv("ALLOWED_DOMAIN", "charlotte.edu").lower()

intents = discord.Intents.default()
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    await db.init_db()
    if GUILD_ID:
        guild = discord.Object(id=GUILD_ID)
        bot.tree.copy_global_to(guild=guild)
        await bot.tree.sync(guild=guild)
    print(f"Bot connected as {bot.user} (ID: {bot.user.id})")

@bot.tree.command(name="verify", description="Start student verification with your UNCC username (NinerNET ID).")
@app_commands.describe(username="Your UNCC username/NinerNET ID (e.g. jsmith49, without @charlotte.edu)")
async def verify(interaction: discord.Interaction, username: str):
    await interaction.response.defer(ephemeral=True)

    # Strip domain if user typed it by accident
    clean_username = username.strip().lower().split("@")[0]

    if not re.match(r"^[a-zA-Z0-9_\.-]+$", clean_username):
        await interaction.followup.send("❌ Please enter a valid UNCC username (alphanumeric characters only).", ephemeral=True)
        return

    student_email = f"{clean_username}@{ALLOWED_DOMAIN}"
    email_hash = db.hash_email(student_email)

    already_registered, err_msg = await db.check_existing_verification(interaction.user.id, email_hash)
    if already_registered:
        await interaction.followup.send(f"❌ {err_msg}", ephemeral=True)
        return

    # Generate cryptographically secure 6-digit OTP
    otp_code = f"{secrets.randbelow(900000) + 100000}"
    expires_at = time.time() + 600  # 10 minutes

    try:
        await mailer.send_otp_email(student_email, otp_code)
        await db.store_otp(interaction.user.id, email_hash, otp_code, expires_at)
        await interaction.followup.send(
            f"📧 A 6-digit verification code has been sent to `{student_email}`.\n"
            f"Run `/confirm code:<your_code>` within 10 minutes to complete verification.",
            ephemeral=True
        )
    except Exception as ex:
        print(f"SMTP Dispatch Error: {ex}")
        await interaction.followup.send("⚠️ Error sending verification email. Check configuration or alert an admin.", ephemeral=True)

@bot.tree.command(name="confirm", description="Confirm your 6-digit verification passcode.")
@app_commands.describe(code="The 6-digit OTP received in your student email")
async def confirm(interaction: discord.Interaction, code: str):
    await interaction.response.defer(ephemeral=True)

    is_valid, msg = await db.validate_otp(interaction.user.id, code.strip(), time.time())
    if not is_valid:
        await interaction.followup.send(f"❌ {msg}", ephemeral=True)
        return

    guild = interaction.guild
    if not guild:
        await interaction.followup.send("❌ Command must be executed inside the server.", ephemeral=True)
        return

    role = guild.get_role(VERIFIED_ROLE_ID)
    if not role:
        await interaction.followup.send("⚠️ Identity verified, but the target role ID was not found in server settings.", ephemeral=True)
        return

    try:
        member = guild.get_member(interaction.user.id) or await guild.fetch_member(interaction.user.id)
        await member.add_roles(role, reason="Passed university email OTP verification.")
        await interaction.followup.send(f"🎉 {msg} You have been assigned the **{role.name}** role!", ephemeral=True)
    except discord.Forbidden:
        await interaction.followup.send("⚠️ Identity verified, but the bot's role is below the target role in server settings.", ephemeral=True)

if __name__ == "__main__":
    bot.run(DISCORD_TOKEN)