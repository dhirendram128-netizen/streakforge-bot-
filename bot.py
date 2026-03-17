import logging
import random
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    CallbackQueryHandler, ContextTypes, filters
)

BOT_TOKEN = "8612749378:AAGrn7T73flwGOueb3ucGtTiEwuFcratQAc"
UPI_ID = "8948979748@ybl"

users = {}
pairs = {}
waiting_pool = {}
clans = {}

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
        "voice_intro": "🎙 *Voice Mode Activated*\n\nFrom now on, send *voice notes* to your partner.\n\nHearing someone's voice builds 10x stronger connection than text.\n\n*Send your first voice note introducing yourself!*",
        "streak_casino": "🎰 *Streak Casino*\n\nCheck-in karke rewards jeeto!\n\nReady?",
        "partner_match": "🎉 *Partner Matched!*\n\n*AI Compatibility Score: {score}%*\n\nYou both: {common_traits}\n\n*First task:* Send voice note introducing yourself!\n\n*Remember:* Their streak depends on YOU.",
        "break_shield": "🛡 *Break Shield Activated!*\n\nYour streak was breaking... but your *{shield_type}* saved you!\n\nRemaining shields: {count}\n\n*Tomorrow pakka check-in.*",
        "recovery_mode": "🔄 *Recovery Mode*\n\nStreak break hua? No problem.\n\n*3-Day Recovery Challenge:*\nDay 1: 10 min task\nDay 2: 20 min task\nDay 3: Full check-in\n\n*Complete = Original streak RESTORED + Shield bonus*",
        "clan_invite": "🏰 *Join a Clan*\n\nSolo = 3x harder\nClan = 10x accountability\n\n*Active Clans:*\n{clan_list}\n\n/join_clan ClanName",
        "paywall_day5": "⏰ *Your Partner Needs You*\n\n{partner_name} checked in today.\n\n*If you leave, their streak breaks too.*\n\n₹79 = 1 coffee = 30 days transformation\n\n*Payment: {upi}*\nSend screenshot → /paid",
        "forge_welcome": "🤖 *Forge AI Coach*\n\nYour 24/7 accountability partner.\n\nChoose:",
    },
    "hi": {
        "welcome": "🔥 *StreakForge में स्वागत है*\n\nआप कमजोर नहीं हो।\nआप इसलिए फेल होते हो क्योंकि कोई देख नहीं रहा।\n\n*अपना रास्ता चुनें:*",
        "ai_onboard": "🤖 *स्मार्ट सेटअप*\n\n3 सवालों से परफेक्ट गोल बनाएंगे।\n\n*सवाल 1:* मुख्य फोकस क्या है?\n• 💪 फिटनेस\n• 📚 पढ़ाई/करियर\n• 💰 बिजनेस/पैसा\n• 🎯 सेल्फ-डिसिप्लिन",
        "voice_intro": "🎙 *वॉइस मोड ऑन*\n\nअब से *वॉइस नोट्स* भेजो पार्टनर को।\n\nआवाज़ सुनने से 10x ज्यादा कनेक्शन बनता है।\n\n*पहला वॉइस नोट भेजो - खुद का परिचय!*",
        "streak_casino": "🎰 *स्ट्रीक कैसीनो*\n\nचेक-इन करके रिवॉर्ड्स जीतो!\n\nतैयार?",
        "partner_match": "🎉 *पार्टनर मिल गया!*\n\n*AI कम्पैटिबिलिटी स्कोर: {score}%*\n\nआप दोनों: {common_traits}\n\n*पहला टास्क:* वॉइस नोट भेजो!\n\n*याद रखो:* उनका स्ट्रीक आप पर डिपेंड करता है।",
        "break_shield": "🛡 *ब्रेक शील्ड एक्टिवेटेड!*\n\nस्ट्रीक टूट रही थी... लेकिन *{shield_type}* ने बचा लिया!\n\nबचे शील्ड: {count}\n\n*कल पक्का चेक-इन करना।*",
        "recovery_mode": "🔄 *रिकवरी मोड*\n\nस्ट्रीक टूट गई? कोई बात नहीं।\n\n*3-दिन रिकवरी चैलेंज:*\nदिन 1: 10 मिनट\nदिन 2: 20 मिनट\nदिन 3: फुल चेक-इन\n\n*पूरा = ओरिजिनल स्ट्रीक वापस + शील्ड बोनस*",
        "clan_invite": "🏰 *क्लान जॉइन करो*\n\nअकेले = 3x मुश्किल\nक्लान = 10x अकाउंटेबिलिटी\n\n*एक्टिव क्लान:*\n{clan_list}\n\n/join_clan CllanNaam",
        "paywall_day5": "⏰ *पार्टनर को आपकी जरूरत है*\n\n{partner_name} ने आज चेक-इन किया।\n\n*आप नहीं आए तो उनका स्ट्रीक भी टूटेगा।*\n\n₹79 = 1 कॉफी = 30 दिन ट्रांसफॉर्मेशन\n\n*पेमेंट: {upi}*\nस्क्रीनशॉट भेजो → /paid",
        "forge_welcome": "🤖 *फोर्ज AI कोच*\n\nआपका 24/7 अकाउंटेबिलिटी पार्टनर।\n\nक्या चाहिए:",
    }
}

def get_text(user_id, key, **kwargs):
    lang = users.get(user_id, {}).get("lang", "en")
    text = MESSAGES[lang].get(key, MESSAGES["en"][key])
    return text.format(**kwargs) if kwargs else text

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    name = update.effective_user.first_name
    users[user_id] = {
        "name": name,
        "lang": None,
        "goal": None,
        "streak": 0,
        "best_streak": 0,
        "old_streak": 0,
        "shields": {"normal": 0, "legendary": 0},
        "trial_start": datetime.now().isoformat(),
        "paid": False,
        "state": "choose_lang",
        "partner": None,
        "recovery_mode": False,
        "recovery_day": 0,
        "clan": None,
        "last_checkin": None,
        "checkin_count": 0,
        "onboard_step": 0,
        "onboard_data": {},
        "username": update.effective_user.username
    }
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
    lang = "hi" if query.data == "lang_hi" else "en"
    users[user_id]["lang"] = lang
    users[user_id]["state"] = "ai_onboard"
    users[user_id]["onboard_step"] = 1
    await query.edit_message_text(get_text(user_id, "welcome"), parse_mode="Markdown")
    await context.bot.send_message(
        chat_id=user_id,
        text=get_text(user_id, "ai_onboard"),
        parse_mode="Markdown"
    )

async def ai_onboarding(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text
    if user_id not in users:
        await start(update, context)
        return
    state = users[user_id].get("state")
    if state not in ["ai_onboard", "confirm_goal"]:
        return
    step = users[user_id]["onboard_step"]
    data = users[user_id]["onboard_data"]
    if step == 1:
        category_map = {
            "1": "fitness", "💪": "fitness", "fitness": "fitness",
            "2": "study", "📚": "study", "study": "study",
            "3": "business", "💰": "business", "business": "business",
            "4": "discipline", "🎯": "discipline", "discipline": "discipline",
            "self-discipline": "discipline", "self-disciplin": "discipline"
        }
        cat = category_map.get(text.lower().strip(), "discipline")
        data["category"] = cat
        await update.message.reply_text(
            "⏰ *Question 2:* Daily kitna time de sakte ho?\n"
            "• 15 min\n• 30 min\n• 1 hour\n• 2+ hours",
            parse_mode="Markdown"
        )
        users[user_id]["onboard_step"] = 2
    elif step == 2:
        t = text.lower().replace("min", "").replace("+", "").replace("hour", "").strip()
        time_map = {"15": 15, "30": 30, "1": 60, "2": 120}
        minutes = time_map.get(t, 30)
        data["minutes"] = minutes
        await update.message.reply_text(
            "📅 *Question 3:* Target timeline?\n"
            "• 21 days\n• 30 days\n• 90 days\n• 1 year",
            parse_mode="Markdown"
        )
        users[user_id]["onboard_step"] = 3
    elif step == 3:
        days = 21 if "21" in text else 30 if "30" in text else 90 if "90" in text else 365
        data["days"] = days
        goals = {
            "fitness": f"Daily {data['minutes']} min workout for {days} days",
            "study": f"Focused {data['minutes']} min study daily for {days} days",
            "business": f"{data['minutes']} min business building daily for {days} days",
            "discipline": f"{data['minutes']} min discipline practice for {days} days"
        }
        smart_goal = goals[data.get("category", "discipline")]
        users[user_id]["goal"] = smart_goal
        breakdown = generate_breakdown(data.get("category", "discipline"), data["minutes"], days)
        await update.message.reply_text(
            f"🎯 *Your AI-Generated Goal:*\n\n_{smart_goal}_\n\n"
            f"*Smart Breakdown:*\n{breakdown}\n\n"
            f"✅ /accept\n🔄 /modify",
            parse_mode="Markdown"
        )
        users[user_id]["state"] = "confirm_goal"

def generate_breakdown(category, minutes, days):
    if category == "fitness":
        return f"Week 1-2: {minutes//2} min cardio\nWeek 3+: Full {minutes} min\nProgress every 3 days"
    elif category == "study":
        return f"Pomodoro: {max(1, minutes//25)} sessions daily\nWeekly review Sunday\nMock test every 10 days"
    else:
        return f"Daily: Core task ({minutes} min)\nWeekly: Review\nMilestone: Every 10 days"

async def accept_goal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in users:
        await start(update, context)
        return
    users[user_id]["state"] = "pairing"
    await update.message.reply_text(
        get_text(user_id, "voice_intro"), parse_mode="Markdown"
    )
    await try_match(user_id, context)

async def try_match(user_id, context):
    user = users[user_id]
    category = user["onboard_data"].get("category")
    best_match = None
    best_score = 0
    for pid in list(waiting_pool.keys()):
        if pid == user_id:
            continue
        partner = users.get(pid, {})
        score = 50
        if partner.get("onboard_data", {}).get("category") == category:
            score += 30
        if abs(partner.get("onboard_data", {}).get("minutes", 30) - user["onboard_data"].get("minutes", 30)) <= 15:
            score += 20
        if score > best_score:
            best_score = score
            best_match = pid
    if best_match:
        partner_id = best_match
        del waiting_pool[partner_id]
        pairs[user_id] = partner_id
        pairs[partner_id] = user_id
        users[user_id]["partner"] = partner_id
        users[partner_id]["partner"] = user_id
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
            text="⏳ *Finding your perfect match...*\n\nAverage wait: 2-4 hours\n\nMeanwhile: /forge",
            parse_mode="Markdown"
        )

async def checkin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in users:
        await start(update, context)
        return
    trial_start = datetime.fromisoformat(users[user_id]["trial_start"])
    days_used = (datetime.now() - trial_start).days
    if days_used >= 5 and not users[user_id]["paid"]:
        partner = users[user_id].get("partner")
        partner_name = users[partner]["name"] if partner and partner in users else "Your partner"
        await update.message.reply_text(
            get_text(user_id, "paywall_day5", partner_name=partner_name, upi=UPI_ID),
            parse_mode="Markdown"
        )
        if days_used >= 7:
            return
    if users[user_id]["recovery_mode"]:
        await recovery_checkin(update, context)
        return
    last = users[user_id]["last_checkin"]
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
    if value == 2:
        users[user_id]["shields"]["normal"] += 1
    elif value == 3:
        users[user_id]["shields"]["normal"] += 3
    elif value == 4:
        users[user_id]["streak"] += 2
    elif value == 6:
        users[user_id]["shields"]["legendary"] += 1
    users[user_id]["streak"] += 1
    if users[user_id]["streak"] > users[user_id]["best_streak"]:
        users[user_id]["best_streak"] = users[user_id]["streak"]
    users[user_id]["last_checkin"] = datetime.now().isoformat()
    users[user_id]["checkin_count"] += 1
    await query.edit_message_text(
        f"{emoji} *{reward_name}*\n\n{reward_desc}\n\n"
        f"🔥 Streak: {users[user_id]['streak']} days\n"
        f"🏆 Best: {users[user_id]['best_streak']} days",
        parse_mode="Markdown"
    )
    partner_id = users[user_id].get("partner")
    if partner_id and partner_id in users:
        await context.bot.send_message(
            chat_id=partner_id,
            text=f"💪 *{users[user_id]['name']}* rolled *{reward_name}*!\n"
                 f"Streak: {users[user_id]['streak']} 🔥\n\nTera turn: /checkin",
            parse_mode="Markdown"
        )

async def normal_checkin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    await query.answer()
    users[user_id]["streak"] += 1
    if users[user_id]["streak"] > users[user_id]["best_streak"]:
        users[user_id]["best_streak"] = users[user_id]["streak"]
    users[user_id]["last_checkin"] = datetime.now().isoformat()
    users[user_id]["checkin_count"] += 1
    await query.edit_message_text(
        f"✅ *Check-in done!*\n\n"
        f"🔥 Streak: {users[user_id]['streak']} days\n"
        f"🏆 Best: {users[user_id]['best_streak']} days\n\n"
        f"Kal casino roll karo rewards ke liye! 🎰",
        parse_mode="Markdown"
    )
    partner_id = users[user_id].get("partner")
    if partner_id and partner_id in users:
        await context.bot.send_message(
            chat_id=partner_id,
            text=f"✅ *{users[user_id]['name']}* checked in!\n"
                 f"Streak: {users[user_id]['streak']} 🔥\n\nTera turn: /checkin",
            parse_mode="Markdown"
        )

async def handle_streak_break(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    shields = users[user_id]["shields"]
    if shields["legendary"] > 0:
        shields["legendary"] -= 1
        await update.message.reply_text(
            get_text(user_id, "break_shield", shield_type="LEGENDARY Shield", count=shields["legendary"]),
            parse_mode="Markdown"
        )
        return
    elif shields["normal"] > 0:
        shields["normal"] -= 1
        await update.message.reply_text(
            get_text(user_id, "break_shield", shield_type="Normal Shield", count=shields["normal"]),
            parse_mode="Markdown"
        )
        return
    users[user_id]["old_streak"] = users[user_id]["streak"]
    users[user_id]["recovery_mode"] = True
    users[user_id]["recovery_day"] = 0
    users[user_id]["streak"] = 0
    await update.message.reply_text(
        get_text(user_id, "recovery_mode"), parse_mode="Markdown"
    )

async def recovery_checkin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    day = users[user_id]["recovery_day"] + 1
    tasks = {1: "10 minute easy task", 2: "20 minute focused work", 3: "Full goal completion"}
    keyboard = [[InlineKeyboardButton(f"✅ Day {day} Complete", callback_data=f"recovery_{day}")]]
    await update.message.reply_text(
        f"🔄 *Recovery Day {day}/3*\n\nTask: {tasks.get(day, 'Full completion')}\n\nComplete to restore streak!",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )

async def recovery_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    day = int(query.data.split("_")[1])
    await query.answer()
    users[user_id]["recovery_day"] = day
    if day == 3:
        old_streak = users[user_id].get("old_streak", 0)
        users[user_id]["streak"] = old_streak
        users[user_id]["recovery_mode"] = False
        users[user_id]["shields"]["normal"] += 1
        await query.edit_message_text(
            f"🎉 *RECOVERY COMPLETE!*\n\n"
            f"Your {old_streak}-day streak RESTORED! 🔥\n"
            f"Bonus: 1 Shield added! 🛡\n\n"
            f"Stronger than before. Keep going!",
            parse_mode="Markdown"
        )
    else:
        await query.edit_message_text(
            f"✅ Day {day} done! {3 - day} more days to restore.\n\nCome back tomorrow!"
        )

async def forge(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in users:
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
    intent = query.data.replace("forge_", "")
    streak = users.get(user_id, {}).get("streak", 0)
    goal = users.get(user_id, {}).get("goal", "your goal")
    if intent == "motivation":
        if streak < 3:
            msg = FORGE_RESPONSES["motivation"][0]
        elif streak < 10:
            msg = FORGE_RESPONSES["motivation"][1]
        else:
            msg = FORGE_RESPONSES["motivation"][2]
    elif intent == "recovery":
        msg = random.choice(FORGE_RESPONSES["break_recovery"])
    elif intent == "plan":
        msg = (f"🎯 *Your Plan:*\n\n_{goal}_\n\n"
               f"📊 Break this into:\n• Morning: 40%\n• Evening: 60%\n\n"
               f"⚡ Same time daily = habit 3x faster.")
    elif intent == "why":
        msg = ("💭 *Your Original Why:*\n\n"
               "You joined because you were tired of starting and stopping.\n\n"
               "Remember that feeling? Don't go back there. 🔥")
    else:
        msg = "🤖 Keep going. You got this. 💪"
    await query.edit_message_text(msg, parse_mode="Markdown")

async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in users:
        await start(update, context)
        return
    partner_id = users[user_id].get("partner")
    name = users[user_id]["name"]
    if partner_id and partner_id in users:
        await context.bot.forward_message(
            chat_id=partner_id,
            from_chat_id=user_id,
            message_id=update.message.message_id
        )
        await context.bot.send_message(
            chat_id=partner_id,
            text=f"🎙 *{name}* sent you a voice note! Reply karo! 💬\n\n/checkin kiya?",
            parse_mode="Markdown"
        )
        await update.message.reply_text("✅ Voice note partner ko mil gaya! 🎙")
    else:
        await update.message.reply_text(
            "⏳ Abhi partner nahi mila. Jab milega tab voice note bhejo!\n\n/forge se coach se baat karo."
        )

async def clan_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not clans:
        clans["UPSC Warriors"] = {"members": [], "streak": 0, "category": "study"}
        clans["Gym Beasts"] = {"members": [], "streak": 0, "category": "fitness"}
        clans["Hustle Gang"] = {"members": [], "streak": 0, "category": "business"}
        clans["Mind Masters"] = {"members": [], "streak": 0, "category": "discipline"}
    clan_info = "\n".join([
        f"• *{name}* — {len(data['members'])} members 🔥"
        for name, data in clans.items()
    ])
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
    if clan_name not in clans:
        await update.message.reply_text("❌ Clan nahi mila. /clans dekho.")
        return
    old_clan = users[user_id].get("clan")
    if old_clan and old_clan in clans and user_id in clans[old_clan]["members"]:
        clans[old_clan]["members"].remove(user_id)
    clans[clan_name]["members"].append(user_id)
    users[user_id]["clan"] = clan_name
    await update.message.reply_text(
        f"🏰 *{clan_name}* joined!\n\nMembers: {len(clans[clan_name]['members'])} 💪\n\nSaath mein streak banao!",
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
    opponent_id = None
    for uid, data in users.items():
        if data.get("username") == opponent_username:
            opponent_id = uid
            break
    if not opponent_id:
        await update.message.reply_text("❌ User nahi mila. Unhe pehle bot start karna hoga.")
        return
    keyboard = [
        [InlineKeyboardButton("✅ Accept Battle", callback_data=f"accept_battle_{user_id}"),
         InlineKeyboardButton("❌ Decline", callback_data="decline_battle")]
    ]
    await context.bot.send_message(
        chat_id=opponent_id,
        text=f"⚔️ *BATTLE CHALLENGE!*\n\n"
             f"*{users[user_id]['name']}* ne challenge kiya!\n"
             f"7-day streak race\n"
             f"Prize: 30 days Premium 🏆\n\n"
             f"Unka streak: {users[user_id]['streak']} 🔥\n"
             f"Tera streak: {users[opponent_id]['streak']} 🔥",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )
    await update.message.reply_text("⚔️ Challenge bhej diya! Response ka wait karo...")

async def battle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    await query.answer()
    if query.data == "decline_battle":
        await query.edit_message_text("❌ Battle declined.")
        return
    challenger_id = int(query.data.replace("accept_battle_", ""))
    if challenger_id not in users:
        await query.edit_message_text("❌ Challenger not found.")
        return
    await query.edit_message_text(
        f"⚔️ *BATTLE STARTED!*\n\n"
        f"You vs *{users[challenger_id]['name']}*\n\n"
        f"7 days. Daily /checkin. Winner gets Premium!\n\n"
        f"May the best streak win! 🔥",
        parse_mode="Markdown"
    )
    await context.bot.send_message(
        chat_id=challenger_id,
        text=f"⚔️ *{users[user_id]['name']}* accepted your battle!\n\n"
             f"7 days. Daily /checkin. Best of luck! 🔥",
        parse_mode="Markdown"
    )

async def leaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not users:
        await update.message.reply_text("Abhi koi users nahi!")
        return
    sorted_users = sorted(users.items(), key=lambda x: x[1].get("streak", 0), reverse=True)[:5]
    medals = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣"]
    text = "🏆 *TOP 5 STREAKS*\n\n"
    for i, (uid, data) in enumerate(sorted_users):
        text += f"{medals[i]} *{data['name']}* — {data.get('streak', 0)} days 🔥\n"
    await update.message.reply_text(text, parse_mode="Markdown")

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in users:
        await start(update, context)
        return
    u = users[user_id]
    partner_id = u.get("partner")
    if partner_id and partner_id in users:
        partner_info = f"*{users[partner_id]['name']}* (Streak: {users[partner_id]['streak']} 🔥)"
    else:
        partner_info = "None yet ⏳"
    await update.message.reply_text(
        f"📊 *Your Stats*\n\n"
        f"👤 {u['name']}\n"
        f"🎯 Goal: _{u.get('goal', 'Not set yet')}_\n"
        f"🔥 Current Streak: {u['streak']} days\n"
        f"🏆 Best Streak: {u['best_streak']} days\n"
        f"✅ Total Check-ins: {u['checkin_count']}\n"
        f"🛡 Shields: {u['shields']['normal']} normal | {u['shields']['legendary']} legendary\n"
        f"🤝 Partner: {partner_info}\n"
        f"💎 Premium: {'Yes ✅' if u['paid'] else 'Free Trial'}",
        parse_mode="Markdown"
    )

async def paid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in users:
        await update.message.reply_text("❌ Pehle /start karo")
        return
    users[user_id]["paid"] = True
    users[user_id]["trial_start"] = datetime.now().isoformat()
    users[user_id]["shields"]["normal"] += 3
    await update.message.reply_text(
        "✅ *Payment Confirmed!*\n\n"
        "🎉 Premium 30 days activated!\n"
        "🔥 All features unlocked\n"
        "🛡 3 Shields bonus added!\n\n"
        "Continue: /checkin",
        parse_mode="Markdown"
    )
    partner_id = users[user_id].get("partner")
    if partner_id and partner_id in users:
        await context.bot.send_message(
            chat_id=partner_id,
            text=f"💎 *{users[user_id]['name']}* upgraded to Premium!\nStreak together continues! 🔥",
            parse_mode="Markdown"
        )

def main():
    app = Application.builder().token(BOT_TOKEN).build()
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
    print("🤖 StreakForge Bot running...")
    app.run_polling()

if __name__ == "__main__":
    main()
