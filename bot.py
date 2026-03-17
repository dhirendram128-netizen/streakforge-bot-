import logging
import random
import sqlite3
import os
from datetime import datetime, time
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    CallbackQueryHandler, ContextTypes, filters
)
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
import pytz

BOT_TOKEN = os.environ.get("BOT_TOKEN", "APNA_TOKEN_YAHAN")
UPI_ID = os.environ.get("UPI_ID", "8948979748@ybl")
DB_PATH = "/app/data/streakforge.db"
IST = pytz.timezone("Asia/Kolkata")

def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        name TEXT, lang TEXT, goal TEXT,
        streak INTEGER DEFAULT 0,
        best_streak INTEGER DEFAULT 0,
        old_streak INTEGER DEFAULT 0,
        shields_normal INTEGER DEFAULT 0,
        shields_legendary INTEGER DEFAULT 0,
        trial_start TEXT,
        paid INTEGER DEFAULT 0,
        state TEXT DEFAULT 'choose_lang',
        partner_id INTEGER DEFAULT NULL,
        recovery_mode INTEGER DEFAULT 0,
        recovery_day INTEGER DEFAULT 0,
        clan TEXT DEFAULT NULL,
        last_checkin TEXT DEFAULT NULL,
        checkin_count INTEGER DEFAULT 0,
        onboard_step INTEGER DEFAULT 0,
        onboard_category TEXT DEFAULT NULL,
        onboard_minutes INTEGER DEFAULT 30,
        onboard_days INTEGER DEFAULT 30,
        username TEXT DEFAULT NULL
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS clans (
        name TEXT PRIMARY KEY,
        category TEXT,
        streak INTEGER DEFAULT 0
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS clan_members (
        user_id INTEGER,
        clan_name TEXT
    )''')
    conn.commit()
    conn.close()

def get_user(user_id):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
    row = c.fetchone()
    conn.close()
    return dict(row) if row else None

def save_user(u):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''INSERT OR REPLACE INTO users VALUES (
        :user_id,:name,:lang,:goal,
        :streak,:best_streak,:old_streak,
        :shields_normal,:shields_legendary,
        :trial_start,:paid,:state,:partner_id,
        :recovery_mode,:recovery_day,:clan,
        :last_checkin,:checkin_count,
        :onboard_step,:onboard_category,
        :onboard_minutes,:onboard_days,:username
    )''', u)
    conn.commit()
    conn.close()

def new_user(user_id, name, username):
    return {
        "user_id": user_id, "name": name, "lang": None,
        "goal": None, "streak": 0, "best_streak": 0, "old_streak": 0,
        "shields_normal": 0, "shields_legendary": 0,
        "trial_start": datetime.now().isoformat(),
        "paid": 0, "state": "choose_lang", "partner_id": None,
        "recovery_mode": 0, "recovery_day": 0, "clan": None,
        "last_checkin": None, "checkin_count": 0,
        "onboard_step": 0, "onboard_category": None,
        "onboard_minutes": 30, "onboard_days": 30,
        "username": username
    }

def init_clans():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    for name, cat in [("UPSC Warriors","study"),("Gym Beasts","fitness"),("Hustle Gang","business"),("Mind Masters","discipline")]:
        c.execute("INSERT OR IGNORE INTO clans VALUES (?,?,0)", (name, cat))
    conn.commit()
    conn.close()

def get_all_users():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM users")
    rows = c.fetchall()
    conn.close()
    return [dict(r) for r in rows]

waiting_pool = {}

FORGE_RESPONSES = {
    "motivation": [
        "🔥 Bas 4 din aur — habit ban jayegi. Rukna nahi.",
        "💪 Tu akela nahi hai. 500+ log abhi same struggle kar rahe hain.",
        "⚡ 5 deep breaths. 1 glass paani. Phir 10 minute shuru kar."
    ],
    "break_recovery": [
        "💔 Streak break hua? 87% successful logon ne at least 2 breaks liye hain.",
        "🔄 Recovery mode ON. 3-day mini challenge. Complete kiya toh streak wapas.",
        "🎯 Kal se nahi, ABHI se shuru. 10 minute ka task kar."
    ]
}

logging.basicConfig(level=logging.INFO)

MESSAGES = {
    "en": {
        "welcome": "🔥 *Welcome to StreakForge*\n\nYou don't fail because you're weak.\nYou fail because no one is watching.\n\n*Choose your path:*",
        "ai_onboard": "🤖 *Smart Setup*\n\nI'll ask 3 questions to create your perfect goal.\n\n*Question 1:* What's your main focus?\n• 💪 Fitness\n• 📚 Study/Career\n• 💰 Business/Money\n• 🎯 Self-Discipline",
        "voice_intro": "🎙 *Voice Mode Activated*\n\nSend *voice notes* to your partner.\n\nVoice builds 10x stronger connection!\n\n*Send your first voice note now!*",
        "streak_casino": "🎰 *Streak Casino*\n\nCheck-in karke rewards jeeto!\n\nReady?",
        "partner_match": "🎉 *Partner Matched!*\n\n*AI Compatibility Score: {score}%*\n\nYou both: {common_traits}\n\n*First task:* Send voice note!\n\n*Their streak depends on YOU.*",
        "break_shield": "🛡 *Shield Activated!*\n\nYour *{shield_type}* saved your streak!\n\nRemaining: {count}\n\n*Tomorrow pakka check-in.*",
        "recovery_mode": "🔄 *Recovery Mode*\n\n*3-Day Challenge:*\nDay 1: 10 min task\nDay 2: 20 min task\nDay 3: Full check-in\n\n*Complete = Streak RESTORED + Shield*",
        "clan_invite": "🏰 *Join a Clan*\n\nSolo = 3x harder\nClan = 10x accountability\n\n*Active Clans:*\n{clan_list}\n\n/join_clan ClanName",
        "paywall_day5": "⏰ *Your Partner Needs You*\n\n{partner_name} checked in today.\n\n*If you leave, their streak breaks too.*\n\n₹79 = 1 coffee = 30 days transformation\n\n*Payment: {upi}*\nSend screenshot → /paid",
        "forge_welcome": "🤖 *Forge AI Coach*\n\nYour 24/7 accountability partner.\n\nChoose:",
        "morning_reminder": "☀️ *Good Morning {name}!*\n\n🎯 Goal: _{goal}_\n🔥 Streak: {streak} days\n\nAaj ka check-in karo: /checkin\n\n*Partner wait kar raha hai!* 💪",
        "evening_reminder": "🌙 *{name}, aaj check-in kiya?*\n\n🔥 Streak: {streak} days\n⏰ Sirf 2 ghante bache!\n\n👉 /checkin\n\n*Streak mat todna!* 🛡",
        "night_reminder": "🌃 *Last chance {name}!*\n\n🚨 Aaj check-in nahi kiya!\n🔥 Streak: {streak} days at risk!\n\n👉 /checkin\n\n*Kal se nahi — ABHI karo!*",
        "partner_not_checked": "⚠️ *{name} ne aaj check-in nahi kiya!*\n\nUnka streak: {streak} days at risk 😟\n\nEk message bhejo — motivate karo! 💪",
    },
    "hi": {
        "welcome": "🔥 *StreakForge में स्वागत है*\n\nआप कमजोर नहीं हो।\nकोई देख नहीं रहा इसलिए फेल होते हो।\n\n*अपना रास्ता चुनें:*",
        "ai_onboard": "🤖 *स्मार्ट सेटअप*\n\n3 सवाल — परफेक्ट गोल बनेगा।\n\n*सवाल 1:* मुख्य फोकस?\n• 💪 फिटनेस\n• 📚 पढ़ाई/करियर\n• 💰 बिजनेस\n• 🎯 सेल्फ-डिसिप्लिन",
        "voice_intro": "🎙 *वॉइस मोड ऑन*\n\nपार्टनर को *वॉइस नोट्स* भेजो।\n\nआवाज़ = 10x कनेक्शन!\n\n*अभी पहला वॉइस नोट भेजो!*",
        "streak_casino": "🎰 *स्ट्रीक कैसीनो*\n\nचेक-इन करके रिवॉर्ड्स जीतो!\n\nतैयार?",
        "partner_match": "🎉 *पार्टनर मिल गया!*\n\n*AI स्कोर: {score}%*\n\nआप दोनों: {common_traits}\n\n*पहला टास्क:* वॉइस नोट भेजो!\n\n*उनका स्ट्रीक आप पर है।*",
        "break_shield": "🛡 *शील्ड एक्टिव!*\n\n*{shield_type}* ने स्ट्रीक बचाई!\n\nबचे: {count}\n\n*कल पक्का चेक-इन।*",
        "recovery_mode": "🔄 *रिकवरी मोड*\n\n*3-दिन चैलेंज:*\nदिन 1: 10 मिनट\nदिन 2: 20 मिनट\nदिन 3: फुल चेक-इन\n\n*पूरा = स्ट्रीक वापस + शील्ड*",
        "clan_invite": "🏰 *क्लान जॉइन करो*\n\nअकेले = 3x मुश्किल\nक्लान = 10x ताकत\n\n*एक्टिव क्लान:*\n{clan_list}\n\n/join_clan CllanNaam",
        "paywall_day5": "⏰ *पार्टनर को जरूरत है*\n\n{partner_name} ने आज चेक-इन किया।\n\n*आप नहीं आए = उनका स्ट्रीक टूटेगा।*\n\n₹79 = 1 कॉफी = 30 दिन बदलाव\n\n*पेमेंट: {upi}*\n/paid bhejo",
        "forge_welcome": "🤖 *फोर्ज AI कोच*\n\n24/7 अकाउंटेबिलिटी पार्टनर।\n\nक्या चाहिए:",
        "morning_reminder": "☀️ *सुप्रभात {name}!*\n\n🎯 गोल: _{goal}_\n🔥 स्ट्रीक: {streak} दिन\n\nआज का चेक-इन करो: /checkin\n\n*पार्टनर इंतज़ार कर रहा है!* 💪",
        "evening_reminder": "🌙 *{name}, आज चेक-इन किया?*\n\n🔥 स्ट्रीक: {streak} दिन\n⏰ सिर्फ 2 घंटे बचे!\n\n👉 /checkin\n\n*स्ट्रीक मत तोड़ना!* 🛡",
        "night_reminder": "🌃 *आखिरी मौका {name}!*\n\n🚨 आज चेक-इन नहीं किया!\n🔥 स्ट्रीक: {streak} दिन खतरे में!\n\n👉 /checkin\n\n*कल से नहीं — अभी करो!*",
        "partner_not_checked": "⚠️ *{name} ने आज चेक-इन नहीं किया!*\n\nउनकी स्ट्रीक: {streak} दिन खतरे में 😟\n\nएक मैसेज भेजो — मोटिवेट करो! 💪",
    }
}

def get_text(user_id, key, **kwargs):
    u = get_user(user_id)
    lang = u["lang"] if u and u["lang"] else "en"
    text = MESSAGES[lang].get(key, MESSAGES["en"][key])
    return text.format(**kwargs) if kwargs else text

# ============ REMINDER FUNCTIONS ============

async def send_morning_reminder(app):
    """Subah 8 baje — motivation + goal reminder"""
    users = get_all_users()
    for u in users:
        if not u.get("goal"):
            continue
        try:
            await app.bot.send_message(
                chat_id=u["user_id"],
                text=get_text(u["user_id"], "morning_reminder",
                             name=u["name"],
                             goal=u.get("goal","your goal"),
                             streak=u["streak"]),
                parse_mode="Markdown"
            )
        except Exception:
            pass

async def send_evening_reminder(app):
    """Sham 7 baje — checkin reminder"""
    users = get_all_users()
    today = datetime.now(IST).date()
    for u in users:
        if not u.get("goal"):
            continue
        last = u.get("last_checkin")
        if last:
            last_date = datetime.fromisoformat(last).date()
            if last_date == today:
                continue  # Already checked in
        try:
            await app.bot.send_message(
                chat_id=u["user_id"],
                text=get_text(u["user_id"], "evening_reminder",
                             name=u["name"],
                             streak=u["streak"]),
                parse_mode="Markdown"
            )
        except Exception:
            pass

async def send_night_reminder(app):
    """Raat 10 baje — last chance + partner alert"""
    users = get_all_users()
    today = datetime.now(IST).date()
    for u in users:
        if not u.get("goal"):
            continue
        last = u.get("last_checkin")
        already_done = False
        if last:
            last_date = datetime.fromisoformat(last).date()
            if last_date == today:
                already_done = True
        if not already_done:
            try:
                await app.bot.send_message(
                    chat_id=u["user_id"],
                    text=get_text(u["user_id"], "night_reminder",
                                 name=u["name"],
                                 streak=u["streak"]),
                    parse_mode="Markdown"
                )
            except Exception:
                pass
            # Partner ko bhi alert karo
            partner_id = u.get("partner_id")
            if partner_id:
                partner = get_user(partner_id)
                if partner:
                    try:
                        await app.bot.send_message(
                            chat_id=partner_id,
                            text=get_text(partner_id, "partner_not_checked",
                                         name=u["name"],
                                         streak=u["streak"]),
                            parse_mode="Markdown"
                        )
                    except Exception:
                        pass

# ============ BOT FUNCTIONS ============

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    name = update.effective_user.first_name
    username = update.effective_user.username
    u = new_user(user_id, name, username)
    save_user(u)
    keyboard = [
        [InlineKeyboardButton("🇮🇳 हिंदी", callback_data="lang_hi"),
         InlineKeyboardButton("🇺🇸 English", callback_data="lang_en")]
    ]
    await update.message.reply_text(
        "🌍 Choose Language / भाषा चुनें:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def language_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    await query.answer()
    u = get_user(user_id)
    if not u:
        u = new_user(user_id, query.from_user.first_name, query.from_user.username)
    lang = "hi" if query.data == "lang_hi" else "en"
    u["lang"] = lang
    u["state"] = "ai_onboard"
    u["onboard_step"] = 1
    save_user(u)
    await query.edit_message_text(get_text(user_id, "welcome"), parse_mode="Markdown")
    await context.bot.send_message(
        chat_id=user_id,
        text=get_text(user_id, "ai_onboard"),
        parse_mode="Markdown"
    )

async def ai_onboarding(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text
    u = get_user(user_id)
    if not u:
        await start(update, context)
        return
    state = u.get("state")
    if state not in ["ai_onboard", "confirm_goal"]:
        return
    step = u["onboard_step"]
    if step == 1:
        category_map = {
            "1": "fitness", "💪": "fitness", "fitness": "fitness",
            "2": "study", "📚": "study", "study": "study",
            "3": "business", "💰": "business", "business": "business",
            "4": "discipline", "🎯": "discipline", "discipline": "discipline",
            "self-discipline": "discipline", "self-disciplin": "discipline"
        }
        cat = category_map.get(text.lower().strip(), "discipline")
        u["onboard_category"] = cat
        u["onboard_step"] = 2
        save_user(u)
        await update.message.reply_text(
            "⏰ *Question 2:* Daily kitna time?\n• 15 min\n• 30 min\n• 1 hour\n• 2+ hours",
            parse_mode="Markdown"
        )
    elif step == 2:
        t = text.lower().replace("min","").replace("+","").replace("hours","").replace("hour","").replace(" ","").strip()
        time_map = {"15": 15, "30": 30, "1": 60, "2": 120, "60": 60, "120": 120}
        minutes = time_map.get(t, 30)
        u["onboard_minutes"] = minutes
        u["onboard_step"] = 3
        save_user(u)
        await update.message.reply_text(
            "📅 *Question 3:* Target timeline?\n• 21 days\n• 30 days\n• 90 days\n• 1 year",
            parse_mode="Markdown"
        )
    elif step == 3:
        tl = text.lower().replace(" ","")
        if "21" in tl:
            days = 21
        elif "90" in tl:
            days = 90
        elif any(x in tl for x in ["1year","year","365"]):
            days = 365
        else:
            days = 30
        u["onboard_days"] = days
        goals = {
            "fitness": f"Daily {u['onboard_minutes']} min workout for {days} days",
            "study": f"Focused {u['onboard_minutes']} min study for {days} days",
            "business": f"{u['onboard_minutes']} min business work for {days} days",
            "discipline": f"{u['onboard_minutes']} min discipline practice for {days} days"
        }
        cat = u.get("onboard_category") or "discipline"
        smart_goal = goals[cat]
        u["goal"] = smart_goal
        u["state"] = "confirm_goal"
        save_user(u)
        breakdown = generate_breakdown(cat, u["onboard_minutes"], days)
        await update.message.reply_text(
            f"🎯 *Your Goal:*\n\n_{smart_goal}_\n\n*Breakdown:*\n{breakdown}\n\n✅ /accept\n🔄 /modify",
            parse_mode="Markdown"
        )

def generate_breakdown(category, minutes, days):
    if category == "fitness":
        return f"Week 1-2: {minutes//2} min cardio\nWeek 3+: Full {minutes} min\nProgress every 3 days"
    elif category == "study":
        return f"Pomodoro: {max(1,minutes//25)} sessions daily\nWeekly review Sunday\nMock test every 10 days"
    else:
        return f"Daily: Core task ({minutes} min)\nWeekly: Review\nMilestone: Every 10 days"

async def accept_goal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    u = get_user(user_id)
    if not u:
        await start(update, context)
        return
    u["state"] = "pairing"
    save_user(u)
    await update.message.reply_text(get_text(user_id, "voice_intro"), parse_mode="Markdown")
    await try_match(user_id, context)

async def try_match(user_id, context):
    u = get_user(user_id)
    category = u.get("onboard_category")
    best_match = None
    best_score = 0
    for pid in list(waiting_pool.keys()):
        if pid == user_id:
            continue
        partner = get_user(pid)
        if not partner:
            continue
        score = 50
        if partner.get("onboard_category") == category:
            score += 30
        if abs((partner.get("onboard_minutes") or 30) - (u.get("onboard_minutes") or 30)) <= 15:
            score += 20
        if score > best_score:
            best_score = score
            best_match = pid
    if best_match:
        partner_id = best_match
        del waiting_pool[partner_id]
        u["partner_id"] = partner_id
        save_user(u)
        partner = get_user(partner_id)
        partner["partner_id"] = user_id
        save_user(partner)
        traits = ["same focus area", "similar time commitment", "serious about growth"]
        for uid in [user_id, partner_id]:
            await context.bot.send_message(
                chat_id=uid,
                text=get_text(uid, "partner_match", score=best_score, common_traits=", ".join(traits)),
                parse_mode="Markdown"
            )
    else:
        waiting_pool[user_id] = datetime.now()
        await context.bot.send_message(
            chat_id=user_id,
            text="⏳ *Finding your match...*\n\nAverage wait: 2-4 hours\n\nMeanwhile: /forge",
            parse_mode="Markdown"
        )

async def checkin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    u = get_user(user_id)
    if not u:
        await start(update, context)
        return
    trial_start = datetime.fromisoformat(u["trial_start"])
    days_used = (datetime.now() - trial_start).days
    if days_used >= 5 and not u["paid"]:
        partner_id = u.get("partner_id")
        partner = get_user(partner_id) if partner_id else None
        partner_name = partner["name"] if partner else "Your partner"
        await update.message.reply_text(
            get_text(user_id, "paywall_day5", partner_name=partner_name, upi=UPI_ID),
            parse_mode="Markdown"
        )
        if days_used >= 7:
            return
    if u["recovery_mode"]:
        await recovery_checkin(update, context)
        return
    last = u["last_checkin"]
    if last:
        last_date = datetime.fromisoformat(last).date()
        today = datetime.now().date()
        if (today - last_date).days > 1:
            await handle_streak_break(update, context)
            return
    keyboard = [
        [InlineKeyboardButton("🎰 Roll for Rewards", callback_data="casino_roll"),
         InlineKeyboardButton("⏭ Quick Check-in", callback_data="normal_checkin")]
    ]
    await update.message.reply_text(
        get_text(user_id, "streak_casino"),
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )

async def casino_roll(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    await query.answer()
    u = get_user(user_id)
    if not u:
        return
    dice_msg = await context.bot.send_dice(chat_id=user_id, emoji="🎰")
    value = dice_msg.dice.value
    rewards = {
        1: ("Challenge", "Double points tomorrow!", "⚡"),
        2: ("Small Shield", "1 miss protection added", "🛡"),
        3: ("Big Shield", "3 miss protection added", "🛡🛡"),
        4: ("Bonus Streak", "+2 to current streak", "🔥🔥"),
        5: ("Partner Shield", "Both protected 1 day", "👥🛡"),
        6: ("LEGENDARY", "7-day protection + badge", "👑")
    }
    reward_name, reward_desc, emoji = rewards.get(value, ("Standard", "Keep going!", "✅"))
    if value == 2: u["shields_normal"] += 1
    elif value == 3: u["shields_normal"] += 3
    elif value == 4: u["streak"] += 2
    elif value == 6: u["shields_legendary"] += 1
    u["streak"] += 1
    if u["streak"] > u["best_streak"]:
        u["best_streak"] = u["streak"]
    u["last_checkin"] = datetime.now().isoformat()
    u["checkin_count"] += 1
    save_user(u)
    await query.edit_message_text(
        f"{emoji} *{reward_name}*\n\n{reward_desc}\n\n"
        f"🔥 Streak: {u['streak']} days\n🏆 Best: {u['best_streak']} days",
        parse_mode="Markdown"
    )
    partner_id = u.get("partner_id")
    if partner_id:
        partner = get_user(partner_id)
        if partner:
            await context.bot.send_message(
                chat_id=partner_id,
                text=f"💪 *{u['name']}* rolled *{reward_name}*!\nStreak: {u['streak']} 🔥\n\nTera turn: /checkin",
                parse_mode="Markdown"
            )

async def normal_checkin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    await query.answer()
    u = get_user(user_id)
    if not u:
        return
    u["streak"] += 1
    if u["streak"] > u["best_streak"]:
        u["best_streak"] = u["streak"]
    u["last_checkin"] = datetime.now().isoformat()
    u["checkin_count"] += 1
    save_user(u)
    await query.edit_message_text(
        f"✅ *Check-in done!*\n\n🔥 Streak: {u['streak']} days\n🏆 Best: {u['best_streak']} days\n\nKal casino roll karo! 🎰",
        parse_mode="Markdown"
    )
    partner_id = u.get("partner_id")
    if partner_id:
        partner = get_user(partner_id)
        if partner:
            await context.bot.send_message(
                chat_id=partner_id,
                text=f"✅ *{u['name']}* checked in!\nStreak: {u['streak']} 🔥\n\nTera turn: /checkin",
                parse_mode="Markdown"
            )

async def handle_streak_break(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    u = get_user(user_id)
    if not u:
        return
    if u["shields_legendary"] > 0:
        u["shields_legendary"] -= 1
        save_user(u)
        await update.message.reply_text(
            get_text(user_id, "break_shield", shield_type="LEGENDARY Shield", count=u["shields_legendary"]),
            parse_mode="Markdown"
        )
        return
    elif u["shields_normal"] > 0:
        u["shields_normal"] -= 1
        save_user(u)
        await update.message.reply_text(
            get_text(user_id, "break_shield", shield_type="Normal Shield", count=u["shields_normal"]),
            parse_mode="Markdown"
        )
        return
    u["old_streak"] = u["streak"]
    u["recovery_mode"] = 1
    u["recovery_day"] = 0
    u["streak"] = 0
    save_user(u)
    await update.message.reply_text(get_text(user_id, "recovery_mode"), parse_mode="Markdown")

async def recovery_checkin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    u = get_user(user_id)
    day = u["recovery_day"] + 1
    tasks = {1: "10 minute easy task", 2: "20 minute focused work", 3: "Full goal completion"}
    keyboard = [[InlineKeyboardButton(f"✅ Day {day} Complete", callback_data=f"recovery_{day}")]]
    await update.message.reply_text(
        f"🔄 *Recovery Day {day}/3*\n\nTask: {tasks.get(day,'Full completion')}\n\nComplete to restore streak!",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )

async def recovery_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    day = int(query.data.split("_")[1])
    await query.answer()
    u = get_user(user_id)
    u["recovery_day"] = day
    if day == 3:
        old_streak = u.get("old_streak", 0)
        u["streak"] = old_streak
        u["recovery_mode"] = 0
        u["shields_normal"] += 1
        save_user(u)
        await query.edit_message_text(
            f"🎉 *RECOVERY COMPLETE!*\n\n{old_streak}-day streak RESTORED! 🔥\nBonus Shield! 🛡",
            parse_mode="Markdown"
        )
    else:
        save_user(u)
        await query.edit_message_text(f"✅ Day {day} done! {3-day} more days.\n\nCome back tomorrow!")

async def forge(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    u = get_user(user_id)
    if not u:
        await start(update, context)
        return
    keyboard = [
        [InlineKeyboardButton("🔥 Motivation", callback_data="forge_motivation"),
         InlineKeyboardButton("📋 Smart Plan", callback_data="forge_plan")],
        [InlineKeyboardButton("🔄 Recovery Help", callback_data="forge_recovery"),
         InlineKeyboardButton("💭 Why I Started", callback_data="forge_why")]
    ]
    await update.message.reply_text(
        get_text(user_id, "forge_welcome"),
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )

async def forge_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    await query.answer()
    u = get_user(user_id)
    intent = query.data.replace("forge_", "")
    streak = u["streak"] if u else 0
    goal = u["goal"] if u else "your goal"
    if intent == "motivation":
        msg = FORGE_RESPONSES["motivation"][0] if streak < 3 else FORGE_RESPONSES["motivation"][1] if streak < 10 else FORGE_RESPONSES["motivation"][2]
    elif intent == "recovery":
        msg = random.choice(FORGE_RESPONSES["break_recovery"])
    elif intent == "plan":
        msg = f"🎯 *Your Plan:*\n\n_{goal}_\n\n• Morning: 40%\n• Evening: 60%\n\n⚡ Same time daily = habit 3x faster."
    elif intent == "why":
        msg = "💭 *Your Why:*\n\nTired of starting and stopping.\n\nRemember that feeling. Don't go back. 🔥"
    else:
        msg = "🤖 Keep going. You got this. 💪"
    await query.edit_message_text(msg, parse_mode="Markdown")

async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    u = get_user(user_id)
    if not u:
        await start(update, context)
        return
    partner_id = u.get("partner_id")
    name = u["name"]
    if partner_id:
        partner = get_user(partner_id)
        if partner:
            await context.bot.forward_message(
                chat_id=partner_id,
                from_chat_id=user_id,
                message_id=update.message.message_id
            )
            await context.bot.send_message(
                chat_id=partner_id,
                text=f"🎙 *{name}* sent a voice note!\n\n/checkin kiya? 💪",
                parse_mode="Markdown"
            )
            await update.message.reply_text("✅ Voice note partner ko mil gaya! 🎙")
        else:
            await update.message.reply_text("⏳ Partner nahi mila abhi.")
    else:
        await update.message.reply_text("⏳ Partner nahi mila abhi. /forge se coach se baat karo.")

async def clan_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT name, category FROM clans")
    all_clans = c.fetchall()
    clan_info = ""
    for name, cat in all_clans:
        c.execute("SELECT COUNT(*) FROM clan_members WHERE clan_name=?", (name,))
        count = c.fetchone()[0]
        clan_info += f"• *{name}* — {count} members ({cat}) 🔥\n"
    conn.close()
    await update.message.reply_text(
        get_text(user_id, "clan_invite", clan_list=clan_info),
        parse_mode="Markdown"
    )

async def join_clan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not context.args:
        await update.message.reply_text("Usage: /join_clan UPSC Warriors")
        return
    clan_name = " ".join(context.args)
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT name FROM clans WHERE name=?", (clan_name,))
    if not c.fetchone():
        conn.close()
        await update.message.reply_text("❌ Clan nahi mila. /clans dekho.")
        return
    c.execute("DELETE FROM clan_members WHERE user_id=?", (user_id,))
    c.execute("INSERT INTO clan_members VALUES (?,?)", (user_id, clan_name))
    conn.commit()
    c.execute("SELECT COUNT(*) FROM clan_members WHERE clan_name=?", (clan_name,))
    count = c.fetchone()[0]
    conn.close()
    u = get_user(user_id)
    u["clan"] = clan_name
    save_user(u)
    await update.message.reply_text(
        f"🏰 *{clan_name}* joined!\n\nMembers: {count} 💪\n\nSaath mein streak banao!",
        parse_mode="Markdown"
    )

async def challenge(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not context.args:
        await update.message.reply_text(
            "⚔️ *Streak Battle*\n\nUsage: /challenge @username\n\n7-day race. Winner gets 30 days premium!",
            parse_mode="Markdown"
        )
        return
    opponent_username = context.args[0].replace("@", "")
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT user_id, name, streak FROM users WHERE username=?", (opponent_username,))
    row = c.fetchone()
    conn.close()
    if not row:
        await update.message.reply_text("❌ User nahi mila. Unhe pehle bot start karna hoga.")
        return
    opponent_id, opponent_name, opponent_streak = row
    u = get_user(user_id)
    keyboard = [
        [InlineKeyboardButton("✅ Accept Battle", callback_data=f"accept_battle_{user_id}"),
         InlineKeyboardButton("❌ Decline", callback_data="decline_battle")]
    ]
    await context.bot.send_message(
        chat_id=opponent_id,
        text=f"⚔️ *BATTLE CHALLENGE!*\n\n*{u['name']}* ne challenge kiya!\n7-day streak race\nPrize: 30 days Premium 🏆\n\nUnka streak: {u['streak']} 🔥\nTera streak: {opponent_streak} 🔥",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )
    await update.message.reply_text("⚔️ Challenge bhej diya!")

async def battle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    await query.answer()
    if query.data == "decline_battle":
        await query.edit_message_text("❌ Battle declined.")
        return
    challenger_id = int(query.data.replace("accept_battle_", ""))
    challenger = get_user(challenger_id)
    if not challenger:
        await query.edit_message_text("❌ Challenger not found.")
        return
    await query.edit_message_text(
        f"⚔️ *BATTLE STARTED!*\n\nvs *{challenger['name']}*\n\n7 days. Daily /checkin. Best streak wins! 🔥",
        parse_mode="Markdown"
    )
    await context.bot.send_message(
        chat_id=challenger_id,
        text=f"⚔️ Battle accepted! 7 days. Daily /checkin. Best of luck! 🔥"
    )

async def leaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT name, streak FROM users ORDER BY streak DESC LIMIT 5")
    rows = c.fetchall()
    conn.close()
    if not rows:
        await update.message.reply_text("Abhi koi users nahi!")
        return
    medals = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣"]
    text = "🏆 *TOP 5 STREAKS*\n\n"
    for i, (name, streak) in enumerate(rows):
        text += f"{medals[i]} *{name}* — {streak} days 🔥\n"
    await update.message.reply_text(text, parse_mode="Markdown")

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    u = get_user(user_id)
    if not u:
        await start(update, context)
        return
    partner_id = u.get("partner_id")
    partner = get_user(partner_id) if partner_id else None
    partner_info = f"*{partner['name']}* (Streak: {partner['streak']} 🔥)" if partner else "None yet ⏳"
    await update.message.reply_text(
        f"📊 *Your Stats*\n\n"
        f"👤 {u['name']}\n"
        f"🎯 Goal: _{u.get('goal') or 'Not set'}_\n"
        f"🔥 Streak: {u['streak']} days\n"
        f"🏆 Best: {u['best_streak']} days\n"
        f"✅ Check-ins: {u['checkin_count']}\n"
        f"🛡 Shields: {u['shields_normal']} normal | {u['shields_legendary']} legendary\n"
        f"🤝 Partner: {partner_info}\n"
        f"💎 Premium: {'Yes ✅' if u['paid'] else 'Free Trial'}",
        parse_mode="Markdown"
    )

async def paid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    u = get_user(user_id)
    if not u:
        await update.message.reply_text("❌ Pehle /start karo")
        return
    u["paid"] = 1
    u["trial_start"] = datetime.now().isoformat()
    u["shields_normal"] += 3
    save_user(u)
    await update.message.reply_text(
        "✅ *Payment Confirmed!*\n\n🎉 Premium 30 days!\n🛡 3 Shields bonus!\n\n/checkin karo!",
        parse_mode="Markdown"
    )
    partner_id = u.get("partner_id")
    if partner_id:
        partner = get_user(partner_id)
        if partner:
            await context.bot.send_message(
                chat_id=partner_id,
                text=f"💎 *{u['name']}* Premium ho gaya! Streak continues! 🔥",
                parse_mode="Markdown"
            )

def main():
    init_db()
    init_clans()
    app = Application.builder().token(BOT_TOKEN).build()

    # Scheduler setup
    scheduler = AsyncIOScheduler(timezone=IST)
    scheduler.add_job(send_morning_reminder, CronTrigger(hour=8, minute=0, timezone=IST), args=[app])
    scheduler.add_job(send_evening_reminder, CronTrigger(hour=19, minute=0, timezone=IST), args=[app])
    scheduler.add_job(send_night_reminder, CronTrigger(hour=22, minute=0, timezone=IST), args=[app])
    scheduler.start()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("forge", forge))
    app.add_handler(CommandHandler("checkin", checkin))
    app.add_handler(CommandHandler("clans", clan_list))
    app.add_handler(CommandHandler("join_clan", join_clan))
    app.add_handler(CommandHandler("challenge", challenge))
    app.add_handler(CommandHandler("accept", accept_goal))
    app.add_handler(CommandHandler("leaderboard", leaderboard))
    app.add_handler(CommandHandler("stats", stats))
    app.add_handler(CommandHandler("paid", paid))
    app.add_handler(CallbackQueryHandler(language_callback, pattern="^lang_"))
    app.add_handler(CallbackQueryHandler(casino_roll, pattern="^casino_roll$"))
    app.add_handler(CallbackQueryHandler(normal_checkin, pattern="^normal_checkin$"))
    app.add_handler(CallbackQueryHandler(recovery_callback, pattern="^recovery_"))
    app.add_handler(CallbackQueryHandler(forge_callback, pattern="^forge_"))
    app.add_handler(CallbackQueryHandler(battle_callback, pattern="^(accept_battle_|decline_battle)"))
    app.add_handler(MessageHandler(filters.VOICE, handle_voice))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, ai_onboarding))
    print("🤖 StreakForge Bot running with reminders...")
    app.run_polling()

if __name__ == "__main__":
    main()
