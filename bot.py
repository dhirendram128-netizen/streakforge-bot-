import logging
import random
import json
import os
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, Dice
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    CallbackQueryHandler, ContextTypes, filters
)

# ============ CONFIG ============
BOT_TOKEN = "8612749378:AAGrn7T73flwGOueb3ucGtTiEwuFcratQAc"  # @BotFather se naya token lo
UPI_ID = "8948979748@ybl"  # Apna actual UPI daalo

# ============ DATA STORAGE ============
users = {}
pairs = {}
waiting_pool = {}
clans = {}
battles = {}

# AI Coach responses
FORGE_RESPONSES = {
    "motivation": [
        "🔥 Tera 3 din ka streak hai. Bas 4 din aur habit ban jayegi. Rukna nahi.",
        "💪 Tu akela nahi hai. 500+ log abhi same struggle kar rahe hain. Sab experts banenge.",
        "⚡ Energy low hai? 5 deep breaths. 1 glass paani. Phir 10 minute shuru kar. Momentum wapas aayega."
    ],
    "break_recovery": [
        "💔 Streak break hua? Koi baat nahi. 87% successful logon ne at least 2 breaks liye hain.",
        "🔄 Recovery mode ON. 3-day mini challenge. Complete kiya toh original streak + bonus shield.",
        "🎯 Kal se nahi, ABHI se shuru. 10 minute ka task kar. Momentum > Perfection."
    ],
    "confused": [
        "🎯 Goal clear nahi? Bata: (1) Health (2) Study (3) Skill (4) Business",
        "⏰ Kitna time daily de sakta hai? 15 min / 30 min / 1 hour / 2+ hours?",
        "📅 Kab tak result chahiye? 1 month / 3 months / 6 months / 1 year?"
    ]
}

logging.basicConfig(level=logging.INFO)

# ============ LANGUAGE SYSTEM ============
MESSAGES = {
    "en": {
        "welcome": "🔥 *Welcome to StreakForge*\n\nYou don't fail because you're weak.\nYou fail because no one is watching.\n\n*Choose your path:*",
        "ai_onboard": "🤖 *Smart Setup*\n\nI'll ask 3 questions to create your perfect goal.\n\n*Question 1:* What's your main focus?\n• 💪 Fitness\n• 📚 Study/Career  \n• 💰 Business/Money\n• 🎯 Self-Discipline",
        "voice_intro": "🎙 *Voice Mode Activated*\n\nFrom now on, send *voice notes* to your partner.\n\nHearing someone's voice builds 10x stronger connection than text.\n\n*Send your first voice note introducing yourself!*",
        "streak_casino": "🎰 *Streak Casino*\n\nCheck-in karke rewards jeeto:\n\n🎲 Roll the dice → 3-3-3 = *Shield* (1 miss allowed)\n🎲 6-6-6 = *Legendary* (7-day shield)\n🎲 1-1-1 = *Challenge* (double points tomorrow)\n\nReady?",
        "partner_match": "🎉 *Partner Matched!*\n\n*AI Compatibility Score: {score}%*\n\nYou both: {common_traits}\n\n*First task:* Send voice note introducing yourself + your why.\n\n*Remember:* Their streak depends on YOU.",
        "break_shield": "🛡 *Break Shield Activated!*\n\nYour streak was breaking... but your *{shield_type}* saved you!\n\nRemaining shields: {count}\n\n*Don't waste it. Tomorrow pakka check-in.*",
        "recovery_mode": "🔄 *Recovery Mode*\n\nStreak break hua? No problem.\n\n*3-Day Recovery Challenge:*\nDay 1: 10 min task ✅\nDay 2: 20 min task ✅  \nDay 3: Full check-in ✅\n\n*Complete = Original streak RESTORED + 7-day shield*\n\n87% people come back stronger. You will too.",
        "clan_invite": "🏰 *Join a Clan*\n\nSolo = 3x harder\nClan = 10x accountability\n\n*Active Clans:*\n{clan_list}\n\n/join_clan [name] to enter\n/create_clan [name] to build your own",
        "battle_challenge": "⚔️ *Streak Battle*\n\nChallenge accepted: *You vs {opponent}*\n\nRules:\n• 7-day streak race\n• Daily check-in mandatory\n• Miss = instant lose\n• Winner gets: *30 days Premium*\n\n*Battle starts tomorrow 6 AM*",
        "paywall_day5": "⏰ *Your Partner Needs You*\n\n{partner_name} ne aaj check-in kiya. Unhe pata nahi tumhara trial khatam hone wala.\n\n*Agar tum nahi aaye, unka streak bhi break hoga.*\n\n₹79 = 1 coffee\nBut = 30 days transformation + not letting partner down\n\n*Payment: {upi}*\nSend screenshot → /paid",
        "forge_welcome": "🤖 *Forge AI Coach*\n\nI'm your 24/7 accountability partner.\n\nBolo kya chahiye:\n• /motivation - Energy boost\n• /plan - Smart goal breakdown  \n• /recovery - Streak break fix\n• /why - Your original reason\n\n*Type anything or send voice note*",
    },
    "hi": {
        "welcome": "🔥 *StreakForge में स्वागत है*\n\nआप कमजोर नहीं हो।\nआप इसलिए फेल होते हो क्योंकि कोई देख नहीं रहा।\n\n*अपना रास्ता चुनें:*",
        "ai_onboard": "🤖 *स्मार्ट सेटअप*\n\n3 सवालों से परफेक्ट गोल बनाएंगे।\n\n*सवाल 1:* मुख्य फोकस क्या है?\n• 💪 फिटनेस\n• 📚 पढ़ाई/करियर\n• 💰 बिजनेस/पैसा\n• 🎯 सेल्फ-डिसिप्लिन",
        "voice_intro": "🎙 *वॉइस मोड ऑन*\n\nअब से *वॉइस नोट्स* भेजो।\n\nआवाज़ सुनने से 10x ज्यादा कनेक्शन बनता है।\n\n*पहला वॉइस नोट भेजो - खुद का परिचय!*",
        "streak_casino": "🎰 *स्ट्रीक कैसीनो*\n\nचेक-इन करके रिवॉर्ड्स जीतो:\n\n🎲 डाइस रोल करो → 3-3-3 = *शील्ड* (1 मिस अलाउड)\n🎲 6-6-6 = *लेजेंडरी* (7-दिन शील्ड)\n🎲 1-1-1 = *चैलेंज* (कल डबल पॉइंट्स)\n\nतैयार?",
        "partner_match": "🎉 *पार्टनर मिल गया!*\n\n*AI कम्पैटिबिलिटी स्कोर: {score}%*\n\nआप दोनों: {common_traits}\n\n*पहला टास्क:* वॉइस नोट भेजो - खुद का परिचय + अपना 'क्यों'\n\n*याद रखो:* उनका स्ट्रीक आप पर डिपेंड करता है।",
        "break_shield": "🛡 *ब्रेक शील्ड एक्टिवेटेड!*\n\nआपका स्ट्रीक टूट रहा था... लेकिन *{shield_type}* ने बचा लिया!\n\nबचे हुए शील्ड: {count}\n\n*इसे बर्बाद मत करना। कल पक्का चेक-इन करना।*",
        "recovery_mode": "🔄 *रिकवरी मोड*\n\nस्ट्रीक टूट गई? कोई बात नहीं।\n\n*3-दिन रिकवरी चैलेंज:*\nदिन 1: 10 मिनट टास्क ✅\nदिन 2: 20 मिनट टास्क ✅\nदिन 3: फुल चेक-इन ✅\n\n*पूरा करने पर = ओरिजिनल स्ट्रीक वापस + 7-दिन शील्ड*\n\n87% लोग और मजबूत बनकर वापस आते हैं। आप भी आएंगे।",
        "clan_invite": "🏰 *क्लान जॉइन करो*\n\nअकेले = 3x मुश्किल\nक्लान = 10x अकाउंटेबिलिटी\n\n*एक्टिव क्लान:*\n{clan_list}\n\n/join_clan [नाम] से जुड़ो\n/create_clan [नाम] से अपना बनाओ",
        "battle_challenge": "⚔️ *स्ट्रीक बैटल*\n\nचैलेंज एक्सेप्टेड: *आप vs {opponent}*\n\nनियम:\n• 7-दिन स्ट्रीक रेस\n• रोज चेक-इन जरूरी\n• मिस = तुरंत हार\n• विजेता को: *30 दिन प्रीमियम*\n\n*बैटल कल सुबह 6 बजे शुरू*",
        "paywall_day5": "⏰ *आपके पार्टनर को आपकी जरूरत है*\n\n{partner_name} ने आज चेक-इन किया। उन्हें पता नहीं आपका ट्रायल खत्म हो रहा है।\n\n*अगर आप नहीं आए, उनका स्ट्रीक भी टूट जाएगा।*\n\n₹79 = 1 कॉफी\nलेकिन = 30 दिन ट्रांसफॉर्मेशन + पार्टनर को निराश न करना\n\n*पेमेंट: {upi}*\nस्क्रीनशॉट भेजो → /paid",
        "forge_welcome": "🤖 *फोर्ज AI कोच*\n\nआपका 24/7 अकाउंटेबिलिटी पार्टनर।\n\nक्या चाहिए:\n• /motivation - एनर्जी बूस्ट\n• /plan - स्मार्ट गोल प्लान\n• /recovery - स्ट्रीक टूटने का इलाज\n• /why - आपका ओरिजिनल रीजन\n\n*कुछ भी टाइप करो या वॉइस नोट भेजो*",
    }
}

def get_text(user_id, key, **kwargs):
    lang = users.get(user_id, {}).get("lang", "en")
    text = MESSAGES[lang].get(key, MESSAGES["en"][key])
    return text.format(**kwargs) if kwargs else text

# ============ CORE FUNCTIONS ============

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    name = update.effective_user.first_name
    
    # Reset or new user
    users[user_id] = {
        "name": name,
        "lang": None,
        "goal": None,
        "streak": 0,
        "best_streak": 0,
        "shields": {"normal": 0, "legendary": 0},
        "trial_start": datetime.now().isoformat(),
        "paid": False,
        "state": "choose_lang",
        "partner": None,
        "voice_mode": False,
        "recovery_mode": False,
        "recovery_day": 0,
        "clan": None,
        "battle": None,
        "last_checkin": None,
        "checkin_count": 0,
        "onboard_step": 0,
        "onboard_data": {}
    }
    
    # Language selection
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
    
    # AI Onboarding starts
    users[user_id]["state"] = "ai_onboard"
    users[user_id]["onboard_step"] = 1
    
    await query.edit_message_text(get_text(user_id, "welcome"), parse_mode="Markdown")
    await context.bot.send_message(
        chat_id=user_id,
        text=get_text(user_id, "ai_onboard"),
        parse_mode="Markdown"
    )

async def ai_onboarding(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Smart goal creation through conversation"""
    user_id = update.effective_user.id
    text = update.message.text
    step = users[user_id]["onboard_step"]
    data = users[user_id]["onboard_data"]
    
    if step == 1:  # Category selection
        category_map = {
            "1": "fitness", "💪": "fitness", "fitness": "fitness",
            "2": "study", "📚": "study", "study": "study",
            "3": "business", "💰": "business", "business": "business",
            "4": "discipline", "🎯": "discipline", "discipline": "discipline"
        }
        
        cat = category_map.get(text.lower().strip(), "discipline")
        data["category"] = cat
        
        await update.message.reply_text(
            "⏰ *Question 2:* Daily kitna time de sakte ho?\n"
            "• 15 min (Micro habits)\n"
            "• 30 min (Solid progress)\n"
            "• 1 hour (Serious mode)\n"
            "• 2+ hours (Beast mode)",
            parse_mode="Markdown"
        )
        users[user_id]["onboard_step"] = 2
        
    elif step == 2:  # Time commitment
        time_map = {"15": 15, "30": 30, "1": 60, "2": 120}
        minutes = time_map.get(text.replace("min", "").replace("+", "").strip(), 30)
        data["minutes"] = minutes
        
        await update.message.reply_text(
            "📅 *Question 3:* Target timeline?\n"
            "• 21 days (Habit foundation)\n"
            "• 30 days (Real transformation)\n"
            "• 90 days (Identity change)\n"
            "• 1 year (Life change)",
            parse_mode="Markdown"
        )
        users[user_id]["onboard_step"] = 3
        
    elif step == 3:  # Timeline + Generate goal
        days = 30 if "30" in text else 21 if "21" in text else 90 if "90" in text else 365
        data["days"] = days
        
        # AI-generated smart goal
        goals = {
            "fitness": f"Daily {data['minutes']} min workout for {days} days",
            "study": f"Focused {data['minutes']} min study daily for {days} days",
            "business": f"{data['minutes']} min business building daily for {days} days",
            "discipline": f"{data['minutes']} min discipline practice for {days} days"
        }
        
        smart_goal = goals[data["category"]]
        users[user_id]["goal"] = smart_goal
        
        # Smart breakdown
        breakdown = generate_breakdown(data["category"], data["minutes"], days)
        
        await update.message.reply_text(
            f"🎯 *Your AI-Generated Goal:*\n\n_{smart_goal}_\n\n"
            f"*Smart Breakdown:*\n{breakdown}\n\n"
            f"✅ Accept goal: /accept\n"
            f"🔄 Modify: /modify",
            parse_mode="Markdown"
        )
        users[user_id]["state"] = "confirm_goal"

def generate_breakdown(category, minutes, days):
    """AI-style smart breakdown"""
    if category == "fitness":
        return (f"Week 1-2: {minutes//2} min cardio + stretching\n"
                f"Week 3-4: Full {minutes} min workout\n"
                f"Progressive overload every 3 days")
    elif category == "study":
        return (f"Pomodoro: {minutes//25} sessions daily\n"
                f"Weekly review every Sunday\n"
                f"Mock test every 10 days")
    else:
        return (f"Daily: Core task ({minutes} min)\n"
                f"Weekly: Review + adjust\n"
                f"Milestone: Every 10 days")

async def accept_goal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Goal accepted - move to pairing"""
    user_id = update.effective_user.id
    users[user_id]["state"] = "pairing"
    
    # Activate voice mode
    users[user_id]["voice_mode"] = True
    
    await update.message.reply_text(
        get_text(user_id, "voice_intro"),
        parse_mode="Markdown"
    )
    
    # Try to find match
    await try_match(user_id, context)

async def try_match(user_id, context):
    """AI matching algorithm"""
    user = users[user_id]
    category = user["onboard_data"].get("category")
    
    # Find best match in waiting pool
    best_match = None
    best_score = 0
    
    for pid in list(waiting_pool.keys()):
        if pid == user_id:
            continue
            
        partner = users[pid]
        score = 50  # Base compatibility
        
        # Category match = +30
        if partner["onboard_data"].get("category") == category:
            score += 30
            
        # Time commitment match = +20
        if abs(partner["onboard_data"].get("minutes", 30) - user["onboard_data"].get("minutes", 30)) <= 15:
            score += 20
            
        if score > best_score:
            best_score = score
            best_match = pid
    
    if best_match:
        # Create pair
        partner_id = best_match
        del waiting_pool[partner_id]
        
        pairs[user_id] = partner_id
        pairs[partner_id] = user_id
        users[user_id]["partner"] = partner_id
        users[partner_id]["partner"] = user_id
        
        # Determine common traits
        traits = []
        if users[partner_id]["onboard_data"].get("category") == category:
            traits.append("same focus area")
        traits.append("similar time commitment")
        traits.append("serious about growth")
        
        # Notify both
        for uid, pid in [(user_id, partner_id), (partner_id, user_id)]:
            await context.bot.send_message(
                chat_id=uid,
                text=get_text(uid, "partner_match", 
                            score=best_score,
                            common_traits=", ".join(traits)),
                parse_mode="Markdown"
            )
    else:
        # Add to waiting pool
        waiting_pool[user_id] = datetime.now()
        await context.bot.send_message(
            chat_id=user_id,
            text="⏳ *Finding your perfect match...*\n\n"
                 "AI is analyzing compatibility scores from active users.\n"
                 "Average wait: 2-4 hours\n\n"
                 "Meanwhile: /forge for AI coaching",
            parse_mode="Markdown"
        )

async def checkin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Enhanced check-in with casino"""
    user_id = update.effective_user.id
    
    if user_id not in users:
        await start(update, context)
        return
    
    # Check trial
    trial_start = datetime.fromisoformat(users[user_id]["trial_start"])
    days_used = (datetime.now() - trial_start).days
    
    # Paywall psychology - day 5, 6, 7
    if days_used >= 5 and not users[user_id]["paid"]:
        partner = users[user_id].get("partner")
        partner_name = users[partner]["name"] if partner else "Your partner"
        
        await update.message.reply_text(
            get_text(user_id, "paywall_day5", 
                    partner_name=partner_name,
                    upi=UPI_ID),
            parse_mode="Markdown"
        )
        
        if days_used >= 7:
            return  # Hard stop after 7 days
    
    # Check recovery mode
    if users[user_id]["recovery_mode"]:
        await recovery_checkin(update, context)
        return
    
    # Check for streak break (missed previous day)
    last = users[user_id]["last_checkin"]
    if last:
        last_date = datetime.fromisoformat(last).date()
        today = datetime.now().date()
        if (today - last_date).days > 1:
            # Streak broken
            await handle_streak_break(update, context)
            return
    
    # Normal check-in with casino
    keyboard = [
        [InlineKeyboardButton("🎰 Roll for Rewards", callback_data="casino_roll"),
         InlineKeyboardButton("⏭ Skip (No reward)", callback_data="normal_checkin")]
    ]
    
    await update.message.reply_text(
        get_text(user_id, "streak_casino"),
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )

async def casino_roll(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Slot machine style rewards"""
    query = update.callback_query
    user_id = query.from_user.id
    await query.answer()
    
    # Send dice animation
    dice_msg = await context.bot.send_dice(chat_id=user_id, emoji="🎰")
    value = dice_msg.dice.value  # 1-6
    
    # Determine reward
    rewards = {
        1: ("Challenge", "Double points tomorrow!", "⚡"),
        2: ("Small Shield", "1 miss protection", "🛡"),
        3: ("Big Shield", "3 miss protection", "🛡🛡"),
        4: ("Bonus Streak", "+2 to current streak", "🔥🔥"),
        5: ("Partner Shield", "Both protected 1 day", "👥🛡"),
        6: ("Legendary", "7-day protection + profile badge", "👑")
    }
    
    reward_name, reward_desc, emoji = rewards.get(value, ("Standard", "Keep going!", "✅"))
    
    # Apply reward
    if value == 2:
        users[user_id]["shields"]["normal"] += 1
    elif value == 3:
        users[user_id]["shields"]["normal"] += 3
    elif value == 6:
        users[user_id]["shields"]["legendary"] += 1
        
    # Update streak
    users[user_id]["streak"] += 1
    if users[user_id]["streak"] > users[user_id]["best_streak"]:
        users[user_id]["best_streak"] = users[user_id]["streak"]
    
    users[user_id]["last_checkin"] = datetime.now().isoformat()
    users[user_id]["checkin_count"] += 1
    
    await query.edit_message_text(
        f"{emoji} *{reward_name}*\n\n{reward_desc}\n\n"
        f"🔥 Streak: {users[user_id]['streak']} days\n"
        f"Best: {users[user_id]['best_streak']} days",
        parse_mode="Markdown"
    )
    
    # Notify partner
    partner_id = users[user_id].get("partner")
    if partner_id:
        await context.bot.send_message(
            chat_id=partner_id,
            text=f"💪 {users[user_id]['name']} rolled *{reward_name}*!\n"
                 f"Their streak: {users[user_id]['streak']} 🔥\n\n"
                 f"Your turn: /checkin",
            parse_mode="Markdown"
        )

async def handle_streak_break(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Smart streak break handling"""
    user_id = update.effective_user.id
    
    # Check for shields
    shields = users[user_id]["shields"]
    if shields["normal"] > 0:
        shields["normal"] -= 1
        await update.message.reply_text(
            get_text(user_id, "break_shield",
                    shield_type="Normal Shield",
                    count=shields["normal"]),
            parse_mode="Markdown"
        )
        return
    elif shields["legendary"] > 0:
        shields["legendary"] -= 1
        await update.message.reply_text(
            get_text(user_id, "break_shield",
                    shield_type="LEGENDARY Shield",
                    count=shields["legendary"]),
            parse_mode="Markdown"
        )
        return
    
    # No shields - offer recovery
    users[user_id]["recovery_mode"] = True
    users[user_id]["recovery_day"] = 0
    users[user_id]["streak"] = 0  # Reset but save best
    
    await update.message.reply_text(
        get_text(user_id, "recovery_mode"),
        parse_mode="Markdown"
    )

async def recovery_checkin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """3-day recovery challenge"""
    user_id = update.effective_user.id
    day = users[user_id]["recovery_day"] + 1
    
    tasks = {
        1: "10 minute easy task",
        2: "20 minute focused work", 
        3: "Full goal completion"
    }
    
    keyboard = [[
        InlineKeyboardButton(f"✅ Day {day} Complete", callback_data=f"recovery_{day}")
    ]]
    
    await update.message.reply_text(
        f"🔄 *Recovery Day {day}/3*\n\n"
        f"Task: {tasks[day]}\n\n"
        f"Complete this to restore your streak!",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )

async def recovery_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle recovery completion"""
    query = update.callback_query
    user_id = query.from_user.id
    day = int(query.data.split("_")[1])
    await query.answer()
    
    users[user_id]["recovery_day"] = day
    
    if day == 3:
        # Recovery complete!
        old_streak = users[user_id].get("old_streak", 10)  # Default if not tracked
        users[user_id]["streak"] = old_streak
        users[user_id]["recovery_mode"] = False
        users[user_id]["shields"]["normal"] += 1  # Bonus shield
        
        await query.edit_message_text(
            "🎉 *RECOVERY COMPLETE!*\n\n"
            f"Your {old_streak}-day streak is RESTORED! 🔥\n"
            "Bonus: 1 Shield added! 🛡\n\n"
            "You're stronger now. Don't break again!",
            parse_mode="Markdown"
        )
    else:
        await query.edit_message_text(
            f"✅ Day {day} complete! {3-day} days to streak restore.\n\n"
            f"Come back tomorrow for Day {day+1}.",
            parse_mode="Markdown"
        )

async def forge(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """AI Coach command"""
    user_id = update.effective_user.id
    
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
    """Handle forge AI responses"""
    query = update.callback_query
    user_id = query.from_user.id
    await query.answer()
    
    intent = query.data.replace("forge_", "")
    
    if intent == "motivation":
        # Personalized motivation
        streak = users[user_id]["streak"]
        responses = FORGE_RESPONSES["motivation"]
        
        if streak < 3:
            msg = responses[0]
        elif streak < 10:
            msg = responses[1]
        else:
            msg = responses[2]
            
    elif intent == "recovery":
        msg = random.choice(FORGE_RESPONSES["break_recovery"])
        
    elif intent == "plan":
        goal = users[user_id]["goal"]
        msg = f"🎯 *Your Plan:*\n\n_{goal}_\n\n📊 Break this into:\n• Morning: 40%\n• Evening: 60%\n\n⚡ Tip: Same time daily = habit formation 3x faster."
        
    elif intent == "why":
        msg = "💭 *Your Original Why:*\n\nYou joined because you were tired of starting and stopping.\n\nRemember that feeling? Don't go back there. 🔥"
    
    await query.edit_message_text(msg, parse_mode="Markdown")

async def clan_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show active clans"""
    user_id = update.effective_user.id
    
    if not clans:
        # Create default clans
        clans["UPSC Warriors"] = {"members": [], "streak": 0, "category": "study"}
        clans["Gym Beasts"] = {"members": [], "streak": 0, "category": "fitness"}
        clans["Hustle Gang"] = {"members": [], "streak": 0, "category": "business"}
    
    clan_info = "\n".join([
        f"• *{name}* ({len(data['members'])}/50 members) - {data['category']}"
        for name, data in clans.items()
    ])
    
    await update.message.reply_text(
        get_text(user_id, "clan_invite", clan_list=clan_info),
        parse_mode="Markdown"
    )

async def join_clan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Join a clan"""
    user_id = update.effective_user.id
    clan_name = " ".join(context.args)
    
    if clan_name not in clans:
        await update.message.reply_text("❌ Clan not found. /clans to see list")
        return
    
    if len(clans[clan_name]["members"]) >= 50:
        await update.message.reply_text("❌ Clan full. Try another or /create_clan")
        return
    
    # Leave old clan if any
    old_clan = users[user_id].get("clan")
    if old_clan and old_clan in clans:
        clans[old_clan]["members"].remove(user_id)
    
    # Join new
    clans[clan_name]["members"].append(user_id)
    users[user_id]["clan"] = clan_name
    
    await update.message.reply_text(
        f"🏰 *Joined {clan_name}!*\n\n"
        f"Clan streak: {clans[clan_name]['streak']} 🔥\n"
        f"Your contribution matters!\n\n"
        f"/clan_chat to talk with members",
        parse_mode="Markdown"
    )

async def challenge(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """1v1 streak battle"""
    user_id = update.effective_user.id
    
    if not context.args:
        await update.message.reply_text(
            "⚔️ *Streak Battle*\n\n"
            "Usage: /challenge @username\n\n"
            "7-day streak race. Winner gets 30 days premium!",
            parse_mode="Markdown"
        )
        return
    
    opponent_username = context.args[0].replace("@", "")
    
    # Find opponent by username (simplified - in production use username index)
    opponent_id = None
    for uid, data in users.items():
        if data.get("username") == opponent_username:
            opponent_id = uid
            break
    
    if not opponent_id:
        await update.message.reply_text("❌ User not found. They must start the bot first.")
        return
    
    # Send challenge
    keyboard = [
        [InlineKeyboardButton("✅ Accept Battle", callback_data=f"accept_battle_{user_id}"),
         InlineKeyboardButton("❌ Decline", callback_data="decline_battle")]
    ]
    
    await context.bot.send_message(
        chat_id=opponent_id,
        text=f"⚔️ *BATTLE CHALLENGE*\n\n"
             f"{users[user_id]['name']} challenged you!\n"
             f"7-day streak race\n"
             f"Prize: 30 days Premium\n\n"
             f"Your streak: {users[opponent_id]['streak']}\n"
             f"Their streak: {users[user_id]['streak']}",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )
    
    await update.message.reply_text("⚔️ Challenge sent! Waiting for response...")

async def paid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Payment confirmation"""
    user_id = update.effective_user.id
    
    if user_id not in users:
        await update.message.reply_text("❌ Pehle /start karo")
        return
    
    users[user_id]["paid"] = True
    users[user_id]["trial_start"] = datetime.now().isoformat()
    
    await update.message.reply_text(
        "✅ *Payment Confirmed!*\n\n"
        "🎉 Premium activated for 30 days!\n"
        "🔥 All features unlocked\n"
        "🛡 Unlimited shields\n"
        "👑 Legendary badge added\n\n"
        "Continue your streak: /checkin",
        parse_mode="Markdown"
    )
    
    partner_id = users[user_id].get("partner")
    if partner_id:
        await context.bot.send_message(
            chat_id=partner_id,
            text=f"💎 {users[user_id]['name']} upgraded to Premium!\n"
                 f"Your streak together continues! 🔥"
        )

# ============ MAIN ============

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    
    # Commands
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("forge", forge))
    app.add_handler(CommandHandler("checkin", checkin))
    app.add_handler(CommandHandler("clans", clan_list))
    app.add_handler(CommandHandler("join_clan", join_clan))
    app.add_handler(CommandHandler("challenge", challenge))
    app.add_handler(CommandHandler("accept", accept_goal))
    app.add_handler(CommandHandler("paid", paid))
    
    # Callbacks
    app.add_handler(CallbackQueryHandler(language_callback, pattern="^lang_"))
    app.add_handler(CallbackQueryHandler(casino_roll, pattern="^casino_roll$"))
    app.add_handler(CallbackQueryHandler(recovery_callback, pattern="^recovery_"))
    app.add_handler(CallbackQueryHandler(forge_callback, pattern="^forge_"))
    
    # Messages
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, ai_onboarding))
    
    print("🤖 StreakForge Bot running...")
    app.run_polling()

if __name__ == "__main__":
    main()

