import os
import discord
from discord.ext import commands
from discord.ui import Button, View
import asyncio
from flask import Flask
import threading

# שרת רקע קטן ל-Render / Railway
app = Flask(__name__)
@app.route('/')
def home(): 
    return "Welcome, Verify & Anti-Link Bot is alive!", 200

def run_flask():
    port = int(os.environ.get("PORT", 10002))
    app.run(host="0.0.0.0", port=port)

# =========================================================
# הגדרות הבוט השני - עודכן עם ה-IDs החדשים שלך!
# =========================================================
TOKEN = os.getenv("TOKEN")
WELCOME_CHANNEL_ID = 1560613422290035776   # חדר הודעות הוולקאם
VERIFIED_ROLE_ID = 1560613411115758194     # רול חבר השרת שמתקבל באימות
ALLOWED_USER_ID = 961945951780630541       # רק המשתמש הזה יכול לזמן את פאנל האימות

# רשימת אתרים מותרים בשרת
ALLOWED_DOMAINS = ["youtube.com", "youtu.be", "tenor.com", "giphy.com", "discord.com"]

# רשימת 4 הרולים של הצוות שמורשים לשלוח קישורים
ALLOWED_ROLES_IDS = [
    1560613411564552345,
    1560613411564552346,
    1560613411564552347,
    1560613411564552348
]
# =========================================================

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix="?", intents=intents)

# --- כפתור מערכת האימות (Verify) המעודכן לחלון מתמשך ---
class VerifyView(View):
    def __init__(self):
        # הגדרת timeout=None כאן היא קריטית בשביל שהכפתור יעבוד תמיד, גם אחרי ריסטארט לבוט!
        super().__init__(timeout=None)

    @discord.ui.button(label="✅ לחץ כאן לאימות חשבון", style=discord.ButtonStyle.success, custom_id="verify_button_bot2_final")
    async def verify_click(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild = interaction.guild
        member = interaction.user
        role = guild.get_role(VERIFIED_ROLE_ID)
        
        if not role:
            await interaction.response.send_message("❌ רול האימות לא נמצא בשרת. ודא שה-ID תקין.", ephemeral=True)
            return
        if role in member.roles:
            await interaction.response.send_message("אתה כבר מאומת בשרת! 🎉", ephemeral=True)
            return

        try:
            await member.add_roles(role)
            await interaction.response.send_message("אומתת בהצלחה! כל ערוצי השרת נפתחו עבורך. 🎉", ephemeral=True)
        except Exception:
            await interaction.response.send_message("❌ שגיאה במתן הרול. ודא שהרול של הבוט נמצא גבוה יותר ברשימת התפקידים בדיסקורד (Roles Hierarchy).", ephemeral=True)

@bot.event
async def on_ready():
    print(f"👋 {bot.user.name} מחובר ומוכן! (וולקאם, אימות ואנטי-קישורים)")
    # רישום ה-View מחדש בזמן עליית הבוט כדי להקשיב לכפתורים ישנים בשרת
    bot.add_view(VerifyView())
    try:
        await bot.tree.sync()
        print("✅ פקודות הסלאש (Slash Commands) סונכרנו בהצלחה!")
    except Exception as e: 
        print(f"שגיאה בסנכרון פקודות: {e}")

# 1. הודעות וולקאם בכניסה לשרת
@bot.event
async def on_member_join(member):
    channel = bot.get_channel(WELCOME_CHANNEL_ID)
    if channel:
        embed = discord.Embed(
            title="👋 ברוך הבא לשרת שלנו!",
            description=f"היי {member.mention}, שמחים שהצטרפת אלינו! 🎉\n\nלחץ על כפתור האימות בערוץ המתאים כדי לקבל גישה מלאה לשרת.",
            color=discord.Color.purple()
        )
        # שימוש ב-display_avatar בטוח למניעת קריסות
        if member.display_avatar:
            embed.set_thumbnail(url=member.display_avatar.url)
            
        embed.add_field(name="שם משתמש:", value=f"`{member.name}`", inline=True)
        embed.add_field(name="מספר חבר:", value=f"`{len(member.guild.members)}`", inline=True)
        await channel.send(content=f"ברוך הבא {member.mention}! ✨", embed=embed)

# 2. מערכת אנטי-קישורים עם החרגות
@bot.event
async def on_message(message):
    # מתעלם מבוטים ומודא שההודעה נשלחה בתוך שרת (ולא בפרטי)
    if message.author.bot or not message.guild:
        return

    if "http://" in message.content.lower() or "https://" in message.content.lower() or "www." in message.content.lower():
        is_allowed = any(domain in message.content.lower() for domain in ALLOWED_DOMAINS)
        
        if message.author.guild_permissions.administrator:
            is_allowed = True
            
        if not is_allowed and hasattr(message.author, 'roles'):
            has_staff_role = any(role.id in ALLOWED_ROLES_IDS for role in message.author.roles)
            if has_staff_role:
                is_allowed = True

        if not is_allowed:
            try:
                await message.delete()
                warn_msg = await message.channel.send(f"❌ {message.author.mention}, שליחת קישורים אסורה כאן (מותר רק לצוות בכיר, יוטיוב וגיפים)!")
                await asyncio.sleep(5)
                await warn_msg.delete()
            except Exception as e: 
                print(f"שגיאה במחיקת הודעה: {e}")
                
    await bot.process_commands(message)

# פקודת סלאש לזימון פאנל האימות
@bot.tree.command(name="setup-verify", description="מציב את פאנל האימות בשרת")
async def setup_verify(interaction: discord.Interaction):
    if interaction.user.id != ALLOWED_USER_ID:
        await interaction.response.send_message("❌ אין לך הרשאה לבצע פקודה זו!", ephemeral=True)
        return
        
    embed = discord.Embed(
        title="מערכת אימות חשבון 🛡️",
        description="ברוכים הבאים! כדי למנוע כניסת בוטים וחשבונות פיקטיביים, אנא לחצו על הכפתור למטה כדי לקבל רול חבר שרת וגישה מלאה לערוצים.",
        color=discord.Color.green()
    )
    await interaction.response.send_message("✅ פאנל האימות שוגר בהצלחה!", ephemeral=True)
    await interaction.channel.send(embed=embed, view=VerifyView())

# הפעלת שרת ה-Flask ברקע
threading.Thread(target=run_flask, daemon=True).start()

# הרצת הבוט
bot.run(TOKEN)
