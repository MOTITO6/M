import telebot
from telebot import types
from telebot.handler_backends import State, StatesGroup
from telebot.storage import StateMemoryStorage
from telebot import custom_filters
import requests
import json
import base64
import xml.etree.ElementTree as ET
import hashlib
import threading
import time
import re
import random
import os
import uuid
import string
import io
from bs4 import BeautifulSoup
from PIL import Image
import logging
from datetime import datetime, timedelta

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

API_TOKEN = '8844483441:AAHpSFw6ku0veZYJFIOwboSmp5K6naJTY_Q'
state_storage = StateMemoryStorage()
bot = telebot.TeleBot(API_TOKEN, state_storage=state_storage)

ADMIN_IDS = [
    8148537777,
    8148537777,
]
USER_LOGS = {}

def load_logs_from_file():
    global USER_LOGS
    try:
        with open('user_logs.json', 'r', encoding='utf-8') as f:
            USER_LOGS = json.load(f)
    except FileNotFoundError:
        USER_LOGS = {}
    except Exception as e:
        logger.error(f"خطأ في تحميل السجلات: {e}")
        USER_LOGS = {}

load_logs_from_file()

CHANNELS = [
    {"id": "@O_IU3", "name": "chat Maro", "url": "https://t.me/O_IU3"},
    {"id": "@I_3UI", "name": "Maro Net Free", "url": "https://t.me/I_3UI"}
]

class UserStates(StatesGroup):
    choose_continent = State()
    choose_country = State()
    choose_server = State()
    get_password_ssh = State()

user_data = {}
ssh_user_data = {}
progress_bars = {}

class AntiBanSystem:
    
    @staticmethod
    def random_delay(min_seconds=0.5, max_seconds=2.0, reason=""):
        delay = random.uniform(min_seconds, max_seconds)
        logger.info(f"⏱️ تأخير {delay:.2f}s - {reason}")
        time.sleep(delay)
        return delay
    
    @staticmethod
    def human_like_delay():
        if random.random() < 0.3:
            time.sleep(random.uniform(1.5, 3.0))
        else:
            time.sleep(random.uniform(0.3, 1.0))
    
    @staticmethod
    def progressive_delay(step_number, total_steps):
        base_delay = 0.3
        progress_factor = step_number / total_steps
        delay = base_delay + (progress_factor * random.uniform(1.0, 2.5))
        time.sleep(delay)
        return delay
    
    @staticmethod
    def think_delay():
        time.sleep(random.uniform(0.2, 0.8))

anti_ban = AntiBanSystem()

class TempMail:
    def __init__(self):
        self.ses = requests.Session()
        self.headers = {
            'User-Agent': "okhttp/4.12.0",
            'Accept-Encoding': "gzip",
            'Content-Type': "application/json"
        }
    
    def create_email(self):
        try:
            payload = {
                "name": ''.join(random.choices(string.ascii_letters + string.digits, k=12)),
                "token": ""
            }
            res = self.ses.post(
                "https://api.internal.temp-mail.io/api/v3/email/new",
                data=json.dumps(payload),
                headers=self.headers,
                timeout=15
            ).json()
            self.email = res['email']
            return True, self.email
        except Exception as e:
            return False, str(e)
    
    def get_messages(self):
        try:
            res = self.ses.get(
                f"https://api.internal.temp-mail.io/api/v3/email/{self.email}/messages",
                headers=self.headers,
                timeout=15
            ).json()
            
            if not res:
                return False, "لا توجد رسائل بعد"
            
            messages = []
            for msg in res:
                messages.append({
                    'subject': msg.get('subject', 'بدون عنوان'),
                    'body': msg.get('body_text', ''),
                    'from': msg.get('from', 'غير معروف'),
                    'date': msg.get('created_at', '')
                })
            return True, messages
        except Exception as e:
            return False, str(e)

def get_user_display_name(user):
    if user.first_name:
        return user.first_name
    elif user.username:
        return f"@{user.username}"
    else:
        return "مستخدم"

def mask_password(password):
    if len(password) <= 2:
        return "*" * len(password)
    return password[0] + "*" * (len(password) - 2) + password[-1]

def delete_message_safe(chat_id, message_id):
    try:
        bot.delete_message(chat_id, message_id)
    except:
        pass

def is_admin(user_id):
    return user_id in ADMIN_IDS

def log_user_activity(chat_id, user_data_dict, network, service_type, result):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    if str(chat_id) not in USER_LOGS:
        USER_LOGS[str(chat_id)] = []
    
    input_data = {}
    
    phone = user_data_dict.get('phone') or user_data_dict.get('number')
    if phone:
        input_data['phone'] = phone
    
    email = user_data_dict.get('email')
    if email:
        input_data['email'] = email
    
    password = None
    if 'password' in user_data_dict:
        password = user_data_dict['password']
    elif 'Password' in user_data_dict:
        password = user_data_dict['Password']
    
    other_data = {}
    for key, value in user_data_dict.items():
        if key not in ['phone', 'email', 'session', 'continents', 'countries', 'servers', 'bundle_info',
                      'number', 'action', 'service', 'network', 'service_type',
                      'broadcast_mode', 'step', 'message_id', 'target_id', 'search_mode',
                      'temp_mail', 'temp_mail_obj']:
            if 'pass' in key.lower() or 'password' in key.lower():
                password = password or value
            else:
                try:
                    other_data[key] = str(value)[:50]
                except:
                    other_data[key] = 'غير قابل للعرض'
    
    if password:
        input_data['password'] = password
    
    if other_data:
        input_data['other_data'] = other_data
    
    log_entry = {
        'timestamp': timestamp,
        'network': network,
        'service': service_type,
        'input_data': input_data,
        'result': str(result)[:200] if result else 'لا توجد نتيجة'
    }
    
    USER_LOGS[str(chat_id)].append(log_entry)
    save_logs_to_file()

def save_logs_to_file():
    try:
        with open('user_logs.json', 'w', encoding='utf-8') as f:
            json.dump(USER_LOGS, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"خطأ في حفظ السجلات: {e}")

def check_subscription(user_id):
    not_subscribed = []
    
    for channel in CHANNELS:
        try:
            chat_member = bot.get_chat_member(channel['id'], user_id)
            if chat_member.status in ['left', 'kicked']:
                not_subscribed.append(channel)
        except Exception as e:
            not_subscribed.append(channel)
    
    return not_subscribed

def get_subscription_markup():
    markup = types.InlineKeyboardMarkup(row_width=1)
    
    for channel in CHANNELS:
        markup.add(types.InlineKeyboardButton(
            text=f"  {channel['name']} ",
            url=channel['url']
        ))
    
    markup.add(types.InlineKeyboardButton(
        text="✅ تحقق من الاشتراك",
        callback_data="check_subscription"
    ))
    
    return markup

def send_subscription_message(chat_id, message_text=None):
    text = message_text or """
⚠️ *يجب الاشتراك في القنوات التالية لاستخدام البوت*

اشترك في القنوات ثم اضغط على زر التحقق 👇
"""
    
    bot.send_message(
        chat_id,
        text,
        reply_markup=get_subscription_markup(),
        parse_mode="Markdown",
        disable_web_page_preview=True
    )

SUCCESS_CODES = ["2255"]
FLEX_BUNDLES = [
    {"number": "1️⃣", "name": "فليكس 40", "id": "Flex_2021_511", "price": 40},
    {"number": "2️⃣", "name": "فليكس 45", "id": "Flex_2024_627", "price": 45},
    {"number": "3️⃣", "name": "فليكس 60", "id": "Flex_2021_513", "price": 60},
    {"number": "4️⃣", "name": "فليكس 70", "id": "Flex_2024_629", "price": 70},
    {"number": "5️⃣", "name": "فليكس 90", "id": "Flex_2021_515", "price": 90},
    {"number": "6️⃣", "name": "فليكس 100", "id": "Flex_2024_631", "price": 100},
    {"number": "7️⃣", "name": "فليكس 130", "id": "Flex_2021_517", "price": 130},
    {"number": "8️⃣", "name": "فليكس 150", "id": "Flex_2024_633", "price": 150},
    {"number": "9️⃣", "name": "فليكس 260", "id": "Flex_2021_523", "price": 260},
    {"number": "🔟", "name": "فليكس 300", "id": "Flex_2024_637", "price": 300}
]

SELFIE_IMAGES = [
    "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=512&h=512&fit=crop&crop=face",
    "https://images.unsplash.com/photo-1494790108377-be9c29b29330?w=512&h=512&fit=crop&crop=face",
    "https://images.unsplash.com/photo-1539571696357-5a69c17a67c6?w=512&h=512&fit=crop&crop=face",
    "https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=512&h=512&fit=crop&crop=face",
    "https://images.unsplash.com/photo-1517841905240-472988babdf9?w=512&h=512&fit=crop&crop=face",
    "https://images.unsplash.com/photo-1506794778202-cad84cf45f1d?w=512&h=512&fit=crop&crop=face",
    "https://images.unsplash.com/photo-1524504388940-b1c1722653e1?w=512&h=512&fit=crop&crop=face",
    "https://images.unsplash.com/photo-1502823403499-6ccfcf4fb453?w=512&h=512&fit=crop&crop=face",
    "https://images.unsplash.com/photo-1489980557514-251d61e3eeb6?w=512&h=512&fit=crop&crop=face",
    "https://images.unsplash.com/photo-1501196354995-cbb51c65aaea?w=512&h=512&fit=crop&crop=face",
    "https://images.unsplash.com/photo-1488426862026-3ee34a7d66df?w=512&h=512&fit=crop&crop=face",
    "https://images.unsplash.com/photo-1491349178582-bf3f5eaeea9c?w=512&h=512&fit=crop&crop=face",
    "https://images.unsplash.com/photo-1463453091185-61582044d556?w=512&h=512&fit=crop&crop=face",
    "https://images.unsplash.com/photo-1521119989659-a83eee488004?w=512&h=512&fit=crop&crop=face",
    "https://images.unsplash.com/photo-1544005313-94ddf0286df2?w=512&h=512&fit=crop&crop=face",
    "https://images.unsplash.com/photo-1519699047748-de8e457a634e?w=512&h=512&fit=crop&crop=face",
    "https://images.unsplash.com/photo-1506277886165-e27fd7c37de9?w=512&h=512&fit=crop&crop=face",
    "https://images.unsplash.com/photo-1492447166138-50c3889fccb1?w=512&h=512&fit=crop&crop=face",
    "https://images.unsplash.com/photo-1485206412256-701ccc5b93ca?w=512&h=512&fit=crop&crop=face",
    "https://images.unsplash.com/photo-1479936343636-73cdc5aae0c3?w=512&h=512&fit=crop&crop=face",
]

def show_progress_bar_with_delay(chat_id, message_id, stop_event, network_name, total_steps=10):
    network_configs = {
        'اتصالات': {
            'stages': [
                (0, 3, '🔄 الاتصال بالخادم...', (0.5, 1.5)),
                (3, 5, '🔐 التحقق من البيانات...', (0.8, 2.0)),
                (5, 7, '📡 معالجة الطلب...', (1.0, 2.5)),
                (7, total_steps, '✅ إنهاء العملية...', (0.5, 1.5))
            ],
            'emoji': '📱',
            'color': '🟢'
        },
        'فودافون': {
            'stages': [
                (0, 4, '🔄 الاتصال بخوادم فودافون...', (0.8, 2.0)),
                (4, 7, '🔐 التحقق من الهوية...', (1.0, 2.5)),
                (7, total_steps, '✅ إنهاء العملية...', (0.5, 1.5))
            ],
            'emoji': '🔴',
            'color': '🔴'
        },
        'اورانج': {
            'stages': [
                (0, 3, '🔄 الاتصال بخوادم اورانج...', (0.6, 1.8)),
                (3, 6, '🔐 جاري المصادقة...', (0.8, 2.0)),
                (6, total_steps, '✅ إنهاء العملية...', (0.5, 1.2))
            ],
            'emoji': '🟠',
            'color': '🟠'
        },
        'WE': {
            'stages': [
                (0, 4, '🔍 الاتصال بخوادم WE...', (0.5, 1.5)),
                (4, 7, '📡 جلب البيانات...', (0.8, 2.0)),
                (7, total_steps, '✅ إنهاء العملية...', (0.4, 1.2))
            ],
            'emoji': '🔵',
            'color': '🔵'
        }
    }
    
    config = network_configs.get(network_name, network_configs['اتصالات'])
    progress = 0
    
    while not stop_event.is_set() and progress < total_steps:
        filled = "▪" * progress
        empty = "▫" * (total_steps - progress)
        percentage = int((progress / total_steps) * 100)
        
        current_stage = None
        for start, end, status, delay_range in config['stages']:
            if start <= progress < end:
                current_stage = status
                min_delay, max_delay = delay_range
                break
        
        if current_stage is None:
            current_stage = "⏳ جاري المعالجة..."
            min_delay, max_delay = 0.3, 1.0
        
        progress_bar = f"[{filled}{empty}] {percentage}%"
        
        try:
            bot.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text=f"{config['color']} *معالجة طلب {network_name}*\n"
                     f"{progress_bar}\n"
                     f"{current_stage}\n\n"
                     f"⏱️ يرجى الانتظار...",
                parse_mode="Markdown"
            )
        except:
            pass
        
        if progress < total_steps - 1:
            delay = random.uniform(min_delay, max_delay)
            
            if random.random() < 0.2:
                delay += random.uniform(0.5, 1.5)
            
            if 3 <= progress <= 6:
                delay += random.uniform(0.3, 1.0)
            
            time.sleep(delay)
        
        progress += 1

def get_auth_token_etisalat(email, password):
    auth_string = f"{email}:{password}"
    return base64.b64encode(auth_string.encode("ascii")).decode("ascii")

def make_headers_etisalat(auth_type, token, build="10650", version="33.1.0"):
    return {
        "applicationVersion": "2",
        "applicationName": "MAB",
        "Accept": "text/xml",
        "Authorization": f"{auth_type} {token}",
        "APP-BuildNumber": build,
        "APP-Version": version,
        "OS-Type": "Android",
        "OS-Version": "12",
        "APP-STORE": "GOOGLE",
        "Is-Corporate": "false",
        "Content-Type": "text/xml; charset=UTF-8",
        "Host": "mab.etisalat.com.eg:11003",
        "Connection": "Keep-Alive",
        "User-Agent": "okhttp/5.0.0-alpha.11",
    }

def execute_v2_gift(number, auth_br, cookie, product_name):
    url = "https://mab.etisalat.com.eg:11003/Saytar/rest/servicemanagement/submitOrderV2"
    payload = f"<?xml version='1.0' encoding='UTF-8' standalone='yes' ?><submitOrderRequest><mabOperation></mabOperation><msisdn>{number}</msisdn><operation>REDEEM</operation><productName>{product_name}</productName></submitOrderRequest>"
    headers = {
        'applicationVersion': '2', 'applicationName': 'MAB', 'Accept': 'text/xml',
        'Cookie': cookie, 'auth': "Bearer " + auth_br, 'Content-Type': 'text/xml; charset=UTF-8',
        'Connection': 'Keep-Alive', 'User-Agent': 'okhttp/5.0.0-alpha.11'
    }
    try:
        res = requests.post(url, headers=headers, data=payload, timeout=30)
        if "true" in res.text:
            return "✅ تم تفعيل الهدية بنجاح! ✨"
        else:
            return "⚠️ العرض مفعل مسبقاً أو غير متاح حالياً."
    except:
        return "❌ خطأ في تفعيل العرض."

def execute_daily_gift(number, token):
    headers = make_headers_etisalat("Basic", token)
    url_gift = f"https://mab.etisalat.com.eg:11003/Saytar/rest/dailyTipsWS/dailyTipsExtraGift?req=%3CdialAndLanguageRequest%3E%3CsubscriberNumber%3E{number}%3C%2FsubscriberNumber%3E%3Clanguage%3E1%3C%2Flanguage%3E%3C%2FdialAndLanguageRequest%3E"
    try:
        response_gift = requests.get(url_gift, headers=headers, timeout=30)
        root = ET.fromstring(response_gift.text)
        daily_gifts = root.findall(".//dailyGift")
        activated_found = False
        for gift in daily_gifts:
            redeemed = gift.find("redeemed").text.lower()
            if redeemed == "true":
                activated_found = True
            elif redeemed == "false" and activated_found:
                gift_id = gift.find(".//param[name='GIFT_ID']/value").text
                amount = gift.find(".//param[name='AMOUNT']/value").text
                url_sub = "https://mab.etisalat.com.eg:11003/Saytar/rest/dailyTipsWS/submitOrder"
                payload = f"""<?xml version='1.0' encoding='UTF-8' standalone='yes' ?>
                <dailyTipsSubmitRequest>
                    <operationId>REDEEM</operationId>
                    <params>
                        <param><name>GIFT_ID</name><value>{gift_id}</value></param>
                        <param><name>AMOUNT</name><value>{amount}</value></param>
                        <param><name>GIFT_TYPE</name><value>DailyTip</value></param>
                        <param><name>GIFT_CATEGORY</name><value>Main</value></param>
                    </params>
                    <productId>DAILY_TIPS_GIFT</productId>
                    <subscriberNumber>{number}</subscriberNumber>
                </dailyTipsSubmitRequest>"""
                res_sub = requests.post(url_sub, data=payload, headers=headers, timeout=30)
                if "true" in res_sub.text.lower():
                    return f"✅ تم تفعيل {amount} ميجا يومية بنجاح! 🎉"
                else:
                    return "❌ فشل تفعيل الهدية."
                break
        return "ℹ️ لا توجد هدايا متاحة للتفعيل حالياً."
    except:
        return "❌ حدث خطأ في نظام الهدايا اليومية."

def process_etisalat_email(message):
    chat_id = message.chat.id
    email = message.text.strip()
    if chat_id not in user_data:
        return
    user_data[chat_id]['email'] = email
    msg = bot.send_message(chat_id, "🔑 الآن أدخل كلمة السر:")
    bot.register_next_step_handler(msg, process_etisalat_password)

def process_etisalat_password(message):
    chat_id = message.chat.id
    password = message.text.strip()
    
    if chat_id not in user_data:
        return
    
    email = user_data[chat_id]['email']
    service_type = user_data[chat_id]['service']
    user_data[chat_id]['password'] = password
    
    try:
        bot.delete_message(chat_id, message.message_id)
    except:
        pass
    
    progress_msg = bot.send_message(
        chat_id,
        "🟢 *بدء معالجة طلب اتصالات*\n"
        "[▫▫▫▫▫▫▫▫▫▫] 0%\n"
        "🔄 جاري التجهيز...\n\n"
        "⏱️ يرجى الانتظار...",
        parse_mode="Markdown"
    )
    
    anti_ban.random_delay(0.5, 2.0, "اتصالات - تأخير قبل بدء العملية")
    
    stop_event = threading.Event()
    progress_thread = threading.Thread(
        target=show_progress_bar_with_delay, 
        args=(chat_id, progress_msg.message_id, stop_event, 'اتصالات')
    )
    progress_thread.start()
    
    try:
        time.sleep(random.uniform(0.8, 2.0))
        
        token = get_auth_token_etisalat(email, password)
        anti_ban.human_like_delay()
        
        h_log = make_headers_etisalat("Basic", token, "964", "27.0.0")
        d_log = '<?xml version="1.0" encoding="UTF-8" standalone="yes" ?><loginRequest><deviceId></deviceId><firstLoginAttempt>true</firstLoginAttempt><modelType></modelType><osVersion></osVersion><platform>Android</platform><udid></udid></loginRequest>'
        
        anti_ban.random_delay(0.5, 1.5, "اتصالات - قبل طلب تسجيل الدخول")
        
        log_res = requests.post(
            "https://mab.etisalat.com.eg:11003/Saytar/rest/authentication/loginWithPlan", 
            headers=h_log, 
            data=d_log,
            timeout=30
        )
        
        if "true" in log_res.text:
            xml_root = ET.fromstring(log_res.text)
            number = xml_root.find("dial").text
            auth_br = log_res.headers.get("auth", "")
            cookie = log_res.headers.get("Set-Cookie", "").split(";")[0]
            
            anti_ban.random_delay(1.0, 2.5, "اتصالات - قبل طلب الخدمة")
            
            if service_type == "social":
                result = execute_v2_gift(number, auth_br, cookie, "DOWNLOAD_GIFT_1_SOCIAL_UNITS")
            elif service_type == "stream":
                result = execute_v2_gift(number, auth_br, cookie, "DOWNLOAD_GIFT_2_STREAMING_UNITS")
            elif service_type == "daily":
                result = execute_daily_gift(number, token)
            else:
                result = "❌ نوع خدمة غير معروف"
            
            log_user_activity(chat_id, user_data[chat_id], 'اتصالات', service_type, result)
            
            stop_event.set()
            progress_thread.join()
            
            time.sleep(0.5)
            
            try:
                bot.edit_message_text(
                    chat_id=chat_id,
                    message_id=progress_msg.message_id,
                    text=f"{result}\n\n📱 الرقم: `{number}`",
                    parse_mode="Markdown"
                )
            except:
                bot.send_message(chat_id, f"{result}\n\n📱 الرقم: `{number}`", parse_mode="Markdown")
        else:
            stop_event.set()
            progress_thread.join()
            
            result = "❌ الإيميل أو كلمة السر غير صحيحة.\n\nتأكد من البيانات وحاول مرة أخرى."
            log_user_activity(chat_id, user_data[chat_id], 'اتصالات', service_type, result)
            
            try:
                bot.edit_message_text(
                    chat_id=chat_id,
                    message_id=progress_msg.message_id,
                    text=result
                )
            except:
                bot.send_message(chat_id, result)
    
    except requests.exceptions.Timeout:
        stop_event.set()
        progress_thread.join()
        result = "⏰ انتهت مهلة الاتصال. حاول مرة أخرى لاحقاً."
        log_user_activity(chat_id, user_data[chat_id], 'اتصالات', service_type, result)
        try:
            bot.edit_message_text(chat_id=chat_id, message_id=progress_msg.message_id, text=result)
        except:
            bot.send_message(chat_id, result)
    
    except Exception as e:
        stop_event.set()
        progress_thread.join()
        result = f"❌ حدث خطأ: {str(e)}"
        log_user_activity(chat_id, user_data[chat_id], 'اتصالات', service_type, result)
        try:
            bot.edit_message_text(chat_id=chat_id, message_id=progress_msg.message_id, text=result)
        except:
            bot.send_message(chat_id, result)
    
    finally:
        if chat_id in user_data:
            del user_data[chat_id]

def login_vodafone(phone, password):
    url = "https://mobile.vodafone.com.eg/auth/realms/vf-realm/protocol/openid-connect/token"
    payload = {
        'grant_type': "password",
        'username': phone,
        'password': password,
        'client_secret': "95fd95fb-7489-4958-8ae6-d31a525cd20a",
        'client_id': "ana-vodafone-app"
    }
    headers = {
        'User-Agent': "okhttp/4.12.0",
        'Accept': "application/json, text/plain, */*",
        'Accept-Encoding': "gzip",
        'silentLogin': "true",
        'x-agent-operatingsystem': "11",
        'clientId': "AnaVodafoneAndroid",
        'Accept-Language': "ar",
        'x-agent-device': "OPPO oppo6779",
        'x-agent-version': "2025.11.1",
        'x-agent-build': "1063",
        'digitalId': "2B8218UYN6RPV",
        'device-id': "70d3004b2bd92694"
    }
    try:
        response = requests.post(url, data=payload, headers=headers, timeout=30)
        if response.status_code == 200:
            data = response.json()
            if "access_token" in data:
                return True, data["access_token"]
            else:
                return False, "لم يتم العثور على access_token في الاستجابة"
        else:
            return False, f"فشل تسجيل الدخول - كود الحالة: {response.status_code}"
    except requests.exceptions.Timeout:
        return False, "انتهت مهلة الاتصال"
    except requests.exceptions.ConnectionError:
        return False, "فشل الاتصال بالخادم"
    except Exception as e:
        return False, f"خطأ غير متوقع: {e}"

def login_vodafone_wc(phone, password):
    url = "https://mobile.vodafone.com.eg/auth/realms/vf-realm/protocol/openid-connect/token"
    payload = {
        'grant_type': "password",
        'username': phone,
        'password': password,
        'client_secret': "dca0pbLUWXVhXR266Gw1iT5rqwvvJQoN",
        'client_id': "AnaVF"
    }
    headers = {
        'User-Agent': "okhttp/4.12.0",
        'Accept': "application/json, text/plain, */*",
        'Accept-Encoding': "gzip",
        'silentLogin': "true",
        'msisdn': phone,
        'x-agent-operatingsystem': "15",
        'clientId': "AnaVodafoneAndroid",
        'Accept-Language': "ar",
        'x-agent-device': "OPPO CPH2565",
        'x-agent-version': "2026.4.1",
        'x-agent-build': "1139",
        'digitalId': "28LZHSGCX7QC4",
        'device-id': "aba8140ecd392169"
    }
    try:
        response = requests.post(url, data=payload, headers=headers, timeout=30)
        if response.status_code == 200:
            try:
                token = response.json()['access_token']
                return True, token
            except:
                return False, "خطأ في الرقم أو كلمة المرور"
        else:
            return False, "خطأ في الرقم أو كلمة المرور"
    except requests.exceptions.Timeout:
        return False, "انتهت مهلة الاتصال"
    except requests.exceptions.ConnectionError:
        return False, "فشل الاتصال بالخادم"
    except Exception as e:
        return False, f"خطأ غير متوقع: {e}"

def activate_flex_bundle(phone, token, bundle_id):
    
    if "2021" in bundle_id:
        foxx = "1"
    else:
        foxx = "2"
    
    if foxx == "2":
        url = "https://mobile.vodafone.com.eg/services/dxl/pom/productOrder"
        headers = {
            'User-Agent': "okhttp/4.12.0",
            'Connection': "Keep-Alive",
            'Accept': "application/json",
            'Accept-Encoding': "gzip",
            'Authorization': f"Bearer {token}",
            'api-version': "v2",
            'device-id': "ba4068643748bc78",
            'x-agent-operatingsystem': "15",
            'clientId': "AnaVodafoneAndroid",
            'x-agent-device': "HONOR ALI-NX1",
            'x-agent-version': "2025.11.1.1",
            'x-agent-build': "1064",
            'msisdn': phone,
            'Accept-Language': "ar",
            'Content-Type': "application/json; charset=UTF-8"
        }
        payload = {
            "channel": {"name": "MobileApp"},
            "orderItem": [{
                "action": "add",
                "product": {
                    "characteristic": [
                        {"name": "LangId", "value": "en"},
                        {"name": "ExecutionType", "value": "Sync"}
                    ],
                    "id": bundle_id,
                    "relatedParty": [{"id": phone, "name": "MSISDN", "role": "Subscriber"}]
                }
            }],
            "@type": "AllInOneOffer"
        }
        
        try:
            response = requests.post(url, json=payload, headers=headers, timeout=40)
            if "In Grace period" in response.text:
                return True, {"code": "2255", "reason": "تم التحويل بنجاح"}, response.status_code
            else:
                try:
                    data = response.json()
                except:
                    data = {"code": str(response.status_code), "reason": response.text[:200]}
                return False, data, response.status_code
        except requests.exceptions.Timeout:
            return False, {"reason": "انتهت مهلة الاتصال"}, 408
        except Exception as e:
            return False, {"reason": str(e)}, 500
    
    else:
        url = "https://mobile.vodafone.com.eg/services/dxl/pom/productOrder"
        payload = {
            "channel": {
                "name": "MobileApp"
            },
            "orderItem": [
                {
                    "action": "insert",
                    "id": bundle_id,
                    "product": {
                        "characteristic": [
                            {
                                "name": "PaymentMethod",
                                "value": "ACP"
                            },
                            {
                                "name": "ACP",
                                "value": "True"
                            },
                            {
                                "name": "SMSID",
                                "value": "MUTE_SMS"
                            }
                        ],
                        "encProductId": "38j0fSpWhgCx0y32HugbMcdxxCJ1w8I65lMhvIxdyPVzm9zFyPRzKx0ZQeFhT2qIzUY52tWBLJx6n2vZq4lo9QuBWEFots1tkuekDEedMChrlc8bDe2ZDLJOMupiWtvm01zcdCq1i8sHmiEcr2Ms9EBKFbgX94V8v5qiINpy1f6r1bykXrzi6Q==",
                        "id": bundle_id,
                        "relatedParty": [
                            {
                                "id": phone,
                                "name": "MSISDN",
                                "role": "Subscriber"
                            }
                        ]
                    },
                    "eCode": 0
                }
            ],
            "@type": "FlexACPRenewal"
        }
        
        headers = {
            'User-Agent': "okhttp/4.12.0",
            'Connection': "Keep-Alive",
            'Accept': "application/json",
            'Accept-Encoding': "gzip",
            'Content-Type': "application/json",
            'api-host': "ProductOrderingManagement",
            'useCase': "FlexACPRenewal",
            'Authorization': f"Bearer {token}",
            'api-version': "v2",
            'device-id': "c3ed6b20e10703fd",
            'x-agent-operatingsystem': "13",
            'clientId': "AnaVodafoneAndroid",
            'x-agent-device': "OPPO CPH2235",
            'x-agent-version': "2026.2.3",
            'x-agent-build': "1117",
            'msisdn': phone,
            'Accept-Language': "ar"
        }
        
        try:
            requests.post(url, json=payload, headers=headers, timeout=40)
            
            url = "https://mobile.vodafone.com.eg/services/dxl/pim/product"
            params = {
                'relatedParty.id': phone,
                '@type': "AllInOne",
                'relatedParty.name': "SubscriptionManagement"
            }
            
            headers = {
                'User-Agent': "okhttp/4.12.0",
                'Connection': "Keep-Alive",
                'Accept': "application/json",
                'Accept-Encoding': "gzip",
                'api-host': "ProductInventoryManagementHost",
                'useCase': "AllInOne",
                'Authorization': f"Bearer {token}",
                'api-version': "v2",
                'device-id': "aba8140ecd392169",
                'x-agent-operatingsystem': "15",
                'clientId': "AnaVodafoneAndroid",
                'x-agent-device': "OPPO CPH2565",
                'x-agent-version': "2026.4.1",
                'x-agent-build': "1139",
                'msisdn': phone,
                'Content-Type': "application/json",
                'Accept-Language': "ar"
            }
            
            response = requests.get(url, params=params, headers=headers, timeout=30)
            data = response.json()
            
            try:
                gg = None
                for item in data:
                    for price in item.get("productPrice", []):
                        if price.get("priceType") == "Recurring":
                            for char in price.get("priceCharacteristic", []):
                                if char.get("name") == "paymentMethod" and char.get("value") == "balance":
                                    gg = item.get("id")
                
                if bundle_id == gg:
                    return True, {"code": "2255", "reason": "تم التحويل بنجاح"}, 200
                else:
                    return False, {"reason": "فشل التحويل - لم يتم تأكيد التفعيل"}, 400
            except:
                return False, {"reason": "فشل التحويل - خطأ في قراءة الرد"}, 400
                
        except requests.exceptions.Timeout:
            return False, {"reason": "انتهت مهلة الاتصال"}, 408
        except Exception as e:
            return False, {"reason": str(e)}, 500

def activate_rollover(phone, token):
    url = "https://mobile.vodafone.com.eg/services/dxl/pom/productOrder"
    payload = {
        "channel": {"name": "MobileApp"},
        "orderItem": [{
            "action": "add",
            "product": {
                "characteristic": [
                    {"name": "LangId", "value": "en"},
                    {"name": "ExecutionType", "value": "Sync"}
                ],
                "id": "FLEX_ROLLOVER",
                "relatedParty": [{"id": phone, "name": "MSISDN", "role": "Subscriber"}]
            }
        }],
        "@type": "AllInOneOffer"
    }
    headers = {
        'User-Agent': "okhttp/4.12.0",
        'Connection': "Keep-Alive",
        'Accept': "application/json",
        'Accept-Encoding': "gzip",
        'Authorization': f"Bearer {token}",
        'api-version': "v2",
        'device-id': "ba4068643748bc78",
        'x-agent-operatingsystem': "15",
        'clientId': "AnaVodafoneAndroid",
        'x-agent-device': "HONOR ALI-NX1",
        'x-agent-version': "2025.11.1.1",
        'x-agent-build': "1064",
        'msisdn': phone,
        'Accept-Language': "ar",
        'Content-Type': "application/json; charset=UTF-8"
    }
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=40)
        try:
            data = response.json()
        except:
            data = {"code": str(response.status_code), "reason": response.text[:200]}
        if data and isinstance(data, dict):
            if data.get("code") in SUCCESS_CODES:
                return True, data, response.status_code
            if response.status_code in (200, 201, 202):
                return True, data, response.status_code
        return False, data, response.status_code
    except requests.exceptions.Timeout:
        return False, {"reason": "انتهت مهلة الاتصال"}, 408
    except Exception as e:
        return False, {"reason": str(e)}, 500

def generate_ai_selfie():
    
    image_url = random.choice(SELFIE_IMAGES)
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "image/webp,image/apng,image/*,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    }
    
    try:
        logger.info(f"📥 جاري تحميل صورة من Unsplash...")
        response = requests.get(image_url, headers=headers, timeout=30)
        response.raise_for_status()
        
        img = Image.open(io.BytesIO(response.content))
        
        img_resized = img.resize((512, 512), Image.LANCZOS)
        
        buffered = io.BytesIO()
        img_resized.save(buffered, format="JPEG", quality=85)
        
        image_base64 = base64.b64encode(buffered.getvalue()).decode("utf-8")
        
        logger.info(f"✅ تم تحميل وتجهيز الصورة بنجاح - الحجم: {len(image_base64)} حرف")
        return True, image_base64
        
    except Exception as e:
        logger.warning(f"⚠️ فشل تحميل الصورة من Unsplash: {str(e)}")
        logger.info("🔄 جاري تجربة صورة احتياطية...")
        
        try:
            backup_url = random.choice(SELFIE_IMAGES)
            response = requests.get(backup_url, headers=headers, timeout=20)
            response.raise_for_status()
            
            img = Image.open(io.BytesIO(response.content))
            img_resized = img.resize((512, 512), Image.LANCZOS)
            
            buffered = io.BytesIO()
            img_resized.save(buffered, format="JPEG", quality=85)
            image_base64 = base64.b64encode(buffered.getvalue()).decode("utf-8")
            
            logger.info(f"✅ تم تحميل الصورة الاحتياطية بنجاح")
            return True, image_base64
            
        except Exception as e2:
            logger.error(f"❌ فشل تحميل الصورة الاحتياطية: {str(e2)}")
            logger.info("🔄 استخدام طريقة الطوارئ لتوليد صورة...")
            return generate_fallback_image()

def generate_fallback_image():
    try:
        logger.info("🎨 توليد صورة ملونة عشوائية...")
        
        img = Image.new('RGB', (512, 512), color=(
            random.randint(50, 200),
            random.randint(50, 200),
            random.randint(50, 200)
        ))
        
        from PIL import ImageDraw
        draw = ImageDraw.Draw(img)
        
        for _ in range(500):
            x = random.randint(0, 511)
            y = random.randint(0, 511)
            color = (
                random.randint(0, 255),
                random.randint(0, 255),
                random.randint(0, 255)
            )
            draw.point((x, y), fill=color)
        
        for _ in range(random.randint(3, 8)):
            x = random.randint(50, 462)
            y = random.randint(50, 462)
            r = random.randint(20, 80)
            color = (
                random.randint(50, 200),
                random.randint(50, 200),
                random.randint(50, 200)
            )
            draw.ellipse([x-r, y-r, x+r, y+r], fill=color)
        
        buffered = io.BytesIO()
        img.save(buffered, format="JPEG", quality=90)
        image_base64 = base64.b64encode(buffered.getvalue()).decode("utf-8")
        
        logger.info(f"✅ تم توليد صورة الطوارئ بنجاح - الحجم: {len(image_base64)} حرف")
        return True, image_base64
        
    except Exception as e:
        logger.error(f"❌ فشل توليد الصورة البديلة: {str(e)}")
        return False, "فشل في توليد الصورة"

def activate_daily_500mb(phone, token):
    try:
        logger.info(f"🎯 بدء تفعيل 500 ميجا يومية للرقم {phone}")
        
        logger.info("📸 جاري تجهيز صورة عشوائية...")
        success, image_data = generate_ai_selfie()
        
        if not success:
            return False, f"فشل في تجهيز الصورة: {image_data}"
        
        image_base64 = image_data
        logger.info(f"📸 تم تجهيز الصورة بنجاح - الحجم: {len(image_base64)} حرف base64")
        
        logger.info("🎯 جاري جلب بيانات المسابقة...")
        
        url = "https://web.vodafone.com.eg/services/dxl/promo/promotion"
        params = {
            '@type': "Promo",
            '$.context.type': "worldCupWow26"
        }
        headers = {
            'User-Agent': "vodafoneandroid",
            'Accept': "application/json",
            'Accept-Encoding': "gzip, deflate, br, zstd",
            'sec-ch-ua-platform': "\"Android\"",
            'Authorization': f"Bearer {token}",
            'Accept-Language': "AR",
            'msisdn': phone,
            'sec-ch-ua': "\"Chromium\";v=\"148\", \"Android WebView\";v=\"148\", \"Not/A)Brand\";v=\"99\"",
            'clientId': "WebsiteConsumer",
            'sec-ch-ua-mobile': "?1",
            'channel': "APP_PORTAL",
            'Content-Type': "application/json",
            'X-Requested-With': "com.emeint.android.myservices",
            'Sec-Fetch-Site': "same-origin",
            'Sec-Fetch-Mode': "cors",
            'Sec-Fetch-Dest': "empty",
            'Referer': "https://web.vodafone.com.eg/portal/bf/worldCup26/home?isPostMessages=false",
        }
        
        response = requests.get(url, params=params, headers=headers, timeout=30)
        
        try:
            promo_id = response.json()[0]["id"]
            logger.info(f"✅ تم جلب ID المسابقة: {promo_id}")
        except:
            error_msg = f"فشل في جلب ID المسابقة\nResponse: {response.text[:200]}"
            logger.error(error_msg)
            return False, error_msg
        
        logger.info("📤 جاري إرسال الصورة والبيانات...")
        
        pharaoh_names = [
            "tutankhamun", "ramses", "nefertiti", "cleopatra",
            "akhenaten", "hatshepsut", "khufu", "amenhotep"
        ]
        
        url_submit = "https://web.vodafone.com.eg/services/dxl/pj/wc/journey/promoJourney"
        payload = {
            "@type": "worldCupWow26",
            "id": promo_id,
            "attachment": [
                {
                    "attachmentType": "Image",
                    "content": image_base64,
                    "mimeType": "image/jpeg"
                }
            ],
            "characteristics": [
                {
                    "name": "pharaohName",
                    "value": random.choice(pharaoh_names)
                }
            ]
        }
        headers = {
            'User-Agent': "vodafoneandroid",
            'Accept': "application/json",
            'Accept-Encoding': "gzip, deflate, br, zstd",
            'Content-Type': "application/json",
            'sec-ch-ua-platform': "\"Android\"",
            'Authorization': f"Bearer {token}",
            'Accept-Language': "AR",
            'msisdn': phone,
            'sec-ch-ua': "\"Chromium\";v=\"148\", \"Android WebView\";v=\"148\", \"Not/A)Brand\";v=\"99\"",
            'clientId': "WebsiteConsumer",
            'sec-ch-ua-mobile': "?1",
            'Origin': "https://web.vodafone.com.eg",
            'X-Requested-With': "com.emeint.android.myservices",
            'Sec-Fetch-Site': "same-origin",
            'Sec-Fetch-Mode': "cors",
            'Sec-Fetch-Dest': "empty",
            'Referer': "https://web.vodafone.com.eg/portal/bf/worldCup26/camera?isPostMessages=false",
        }
        
        response_submit = requests.post(
            url_submit, 
            data=json.dumps(payload), 
            headers=headers,
            timeout=30
        )
        
        if response_submit.status_code == 201:
            logger.info(f"✅ تم تفعيل 500 ميجا بنجاح للرقم {phone}")
            return True, "تم تفعيل 500 ميجا بنجاح 🏆"
        else:
            try:
                error_data = response_submit.json()
                error_msg = error_data.get('reason', 'Unknown error')
                logger.error(f"❌ فشل التفعيل: {error_msg}")
                return False, f"فشل التفعيل: {error_msg}"
            except:
                error_msg = f"خطأ غير معروف - Status: {response_submit.status_code}"
                logger.error(error_msg)
                return False, error_msg
            
    except requests.exceptions.Timeout:
        return False, "انتهت مهلة الاتصال"
    except Exception as e:
        logger.error(f"❌ خطأ غير متوقع: {str(e)}")
        return False, f"خطأ: {str(e)[:200]}"

def show_flex_bundles(chat_id, message_id):
    markup = types.InlineKeyboardMarkup(row_width=1)
    for bundle in FLEX_BUNDLES:
        callback_data = f"bundle_{bundle['id']}"
        btn = types.InlineKeyboardButton(f"{bundle['number']} {bundle['name']} - {bundle['price']} جنيه", callback_data=callback_data)
        markup.add(btn)
    markup.add(types.InlineKeyboardButton("🔙 رجوع", callback_data="menu_vodafone"))
    bot.edit_message_text("📱 *أنظمة فليكس المتاحة*\nاختر الباقة المطلوبة للتحويل إليها:", chat_id, message_id, reply_markup=markup, parse_mode="Markdown")

def show_confirm_vodafone(chat_id, message_id, service_type):
    markup = types.InlineKeyboardMarkup(row_width=2)
    if service_type == 'flex':
        bundle_info = user_data.get(chat_id, {}).get('bundle_info', {})
        btn_confirm = types.InlineKeyboardButton("✅ متابعة", callback_data="confirm_flex")
        text = f"""
⚠️ *تأكيد التحويل إلى نظام فليكس*

📦 *الباقة:* {bundle_info.get('name', 'غير معروف')}
💰 *السعر:* {bundle_info.get('price', '?')} جنيه شهرياً

🔴 *تنبيه:* التحويل إلى نظام فليكس يعني تغيير نظامك الحالي
        """
    else:
        btn_confirm = types.InlineKeyboardButton("✅ متابعة", callback_data="confirm_rollover")
        text = """
📦 *تفعيل خدمة تزويد يومين*

ℹ️ *تفاصيل الخدمة:*
• متاحة لمستخدمي أنظمة فليكس فقط
• تمكنك من الحصول على يومين إضافيين عند نفاذ الباقة
        """
    btn_cancel = types.InlineKeyboardButton("❌ إلغاء", callback_data="cancel")
    markup.add(btn_confirm, btn_cancel)
    bot.edit_message_text(text, chat_id, message_id, reply_markup=markup, parse_mode="Markdown")

def request_phone_vodafone(chat_id, message_id, service_type):
    try:
        bot.delete_message(chat_id, message_id)
    except:
        pass
    user_data[chat_id]['service_type'] = service_type
    msg = bot.send_message(chat_id, "📱 *أدخل رقم الهاتف*\nأرسل رقم الهاتف فقط\n*مثال:* 01001234567", parse_mode="Markdown")
    bot.register_next_step_handler(msg, lambda m: validate_vodafone_phone(m, service_type))

def validate_vodafone_phone(message, service_type):
    try:
        phone = message.text.strip()
        if not phone.isdigit() or len(phone) < 10 or len(phone) > 11:
            msg = bot.reply_to(message, "❌ رقم الهاتف يجب أن يكون 10 أو 11 رقم. حاول مرة أخرى:")
            bot.register_next_step_handler(msg, lambda m: validate_vodafone_phone(m, service_type))
            return
        user_data[message.chat.id]['phone'] = phone
        msg = bot.reply_to(message, f"✅ *تم استلام رقم الهاتف:* `{phone}`\n\n🔑 *أدخل كلمة المرور الآن*", parse_mode="Markdown")
        bot.register_next_step_handler(msg, lambda m: process_vodafone_password(m, service_type))
    except Exception as e:
        bot.reply_to(message, "❌ حدث خطأ. استخدم /start للبدء من جديد")

def process_vodafone_password(message, service_type):
    try:
        password = message.text.strip()
        try:
            bot.delete_message(message.chat.id, message.message_id)
        except:
            pass
        chat_id = message.chat.id
        phone = user_data[chat_id]['phone']
        user_data[chat_id]['password'] = password
        masked_password = mask_password(password)
        
        service_names = {
            'flex': "تفعيل باقة فليكس",
            'rollover': "تفعيل خدمة تزويد يومين",
            'daily_500': "تفعيل 500 ميجا كل يوم"
        }
        service_name = service_names.get(service_type, "خدمة فودافون")
        
        anti_ban.random_delay(0.5, 1.5, "فودافون - تأخير قبل بدء المعالجة")
        
        processing_msg = bot.send_message(
            chat_id,
            f"🔴 *{service_name}*\n"
            f"📱 *الرقم:* `{phone}`\n"
            f"🔑 *كلمة المرور:* `{masked_password}`\n\n"
            f"[▫▫▫▫▫▫▫▫▫▫] 0%\n"
            f"⏳ *جاري البدء...*",
            parse_mode="Markdown"
        )
        
        stop_event = threading.Event()
        progress_thread = threading.Thread(
            target=show_progress_bar_with_delay,
            args=(chat_id, processing_msg.message_id, stop_event, 'فودافون')
        )
        progress_thread.start()
        
        time.sleep(random.uniform(1.0, 2.5))
        
        if service_type == 'daily_500':
            success, token_or_error = login_vodafone_wc(phone, password)
        else:
            success, token_or_error = login_vodafone(phone, password)
        
        if not success:
            stop_event.set()
            progress_thread.join()
            result = f"❌ *فشل تسجيل الدخول*\n📱 *الرقم:* `{phone}`\n🔴 *السبب:* {token_or_error}"
            log_user_activity(chat_id, user_data[chat_id], 'فودافون', service_type, result)
            bot.edit_message_text(result, chat_id, processing_msg.message_id, parse_mode="Markdown")
            return
        
        token = token_or_error
        
        anti_ban.random_delay(1.5, 3.0, "فودافون - تأخير بين المصادقة والخدمة")
        
        if service_type == 'flex':
            bundle_id = user_data[chat_id]['bundle_id']
            bundle_info = user_data[chat_id]['bundle_info']
            success, result_data, status_code = activate_flex_bundle(phone, token, bundle_id)
            
            stop_event.set()
            progress_thread.join()
            
            if success:
                result = f"✅✅✅ *تم بنجاح!*\n🎉 *تم التحويل إلى نظام فليكس بنجاح*\n📱 *الرقم:* `{phone}`\n📦 *النظام الجديد:* {bundle_info['name']}\n💰 *القيمة الشهرية:* {bundle_info['price']} جنيه"
            else:
                error_reason = result_data.get("reason", "لا يوجد تفاصيل") if isinstance(result_data, dict) else str(result_data)
                result = f"❌❌❌ *فشل*\n📱 *الرقم:* `{phone}`\n🔴 *السبب:* {error_reason}"
                
        elif service_type == 'rollover':
            success, result_data, status_code = activate_rollover(phone, token)
            
            stop_event.set()
            progress_thread.join()
            
            if success:
                result = f"✅✅✅ *تم بنجاح!*\n🎉 *تم تفعيل خدمة تزويد يومين بنجاح*\n📱 *الرقم:* `{phone}`"
            else:
                error_reason = result_data.get("reason", "لا يوجد تفاصيل") if isinstance(result_data, dict) else str(result_data)
                result = f"❌❌❌ *فشل*\n📱 *الرقم:* `{phone}`\n🔴 *السبب:* {error_reason}"
                
        else:
            success, message_text = activate_daily_500mb(phone, token)
            
            stop_event.set()
            progress_thread.join()
            
            if success:
                result = f"✅✅✅ *تم بنجاح!*\n🎉 *تم تفعيل 500 ميجا كل يوم بنجاح*\n📱 *الرقم:* `{phone}`\n🏆 *عرض كأس العالم 2026*"
            else:
                result = f"❌❌❌ *فشل*\n📱 *الرقم:* `{phone}`\n🔴 *السبب:* {message_text}"
        
        log_user_activity(chat_id, user_data[chat_id], 'فودافون', service_type, result)
        
        time.sleep(random.uniform(0.3, 0.8))
        bot.edit_message_text(result, chat_id, processing_msg.message_id, parse_mode="Markdown")
        
    except Exception as e:
        result = f"❌ حدث خطأ: {str(e)}"
        log_user_activity(message.chat.id, user_data.get(message.chat.id, {}), 'فودافون', service_type, result)
        bot.reply_to(message, result)
    finally:
        if chat_id in user_data:
            del user_data[chat_id]

def run_fawazeer(chat_id, number, password, progress_msg_id):
    stop_event = threading.Event()
    progress_thread = threading.Thread(
        target=show_progress_bar_with_delay, 
        args=(chat_id, progress_msg_id, stop_event, 'اورانج')
    )
    progress_thread.start()
    
    try:
        if chat_id in user_data:
            user_data[chat_id]['password'] = password
        
        anti_ban.random_delay(1.0, 2.5, "اورانج - تأخير قبل تسجيل الدخول")
        
        url = "https://services.orange.eg/SignIn.svc/SignInUser"
        payload = {"appVersion": "9.0.1", "channel": {"ChannelName": "MobinilAndMe", "Password": "ig3yh*mk5l42@oj7QAR8yF"}, "dialNumber": number, "isAndroid": True, "lang": "ar", "password": password}
        headers1 = {'User-Agent': "okhttp/4.10.0", 'Connection': "Keep-Alive", 'Accept-Encoding': "gzip", 'Content-Type': "application/json; charset=UTF-8"}
        response = requests.post(url, data=json.dumps(payload), headers=headers1, timeout=30)
        AccessToken = response.json()['SignInUserResult']['AccessToken']
        
        anti_ban.random_delay(0.8, 2.0, "اورانج - تأخير بعد المصادقة الأولى")
        
        url2 = "https://services.orange.eg/APIs/Profile/api/BasicAuthentication/Generate"
        payload2 = {"ChannelName": "MobinilAndMe", "ChannelPassword": "ig3yh*mk5l42@oj7QAR8yF", "Dial": number, "Language": "ar", "Module": "0", "Password": password}
        headers2 = {'User-Agent': "okhttp/4.10.0", 'Connection': "Keep-Alive", 'Accept-Encoding': "gzip", 'Content-Type': "application/json; charset=UTF-8", 'AppVersion': "9.0.1", 'OsVersion': "13", 'IsAndroid': "true", 'IsEasyLogin': "false", 'Token': AccessToken}
        Token = requests.post(url2, data=json.dumps(payload2), headers=headers2, timeout=30).json()["Token"]
        
        anti_ban.random_delay(1.5, 3.0, "اورانج - تأخير قبل طلب الفوازير")
        
        url3 = "https://services.orange.eg/APIs/Ramadan2024/api/RamadanOffers/Fawazeer/Questions"
        headers3 = {
            'User-Agent': "Mozilla/5.0 (Linux; Android 13; 21061119AG Build/TP1A.220624.014; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/139.0.7258.158 Mobile Safari/537.36",
            'Accept': "application/json, text/plain, */*", 'Accept-Encoding': "gzip, deflate, br, zstd", 'Content-Type': "application/json",
            'sec-ch-ua-platform': "\"Android\"", 'sec-ch-ua': "\"Not;A=Brand\";v=\"99\", \"Android WebView\";v=\"139\", \"Chromium\";v=\"139\"",
            'sec-ch-ua-mobile': "?1", 'Origin': "https://services.orange.eg", 'X-Requested-With': "com.orange.mobinilandmf", 'Sec-Fetch-Site': "same-origin",
            'Sec-Fetch-Mode': "cors", 'Sec-Fetch-Dest': "empty", 'Accept-Language': "ar,en-US;q=0.9,en;q=0.8"
        }
        data = requests.post(url3, data=json.dumps({"Dial": number, "Language": "ar", "Token": Token}), headers=headers3, timeout=30).json()
        
        if data.get('ErrorCode') == 1:
            result = "⚠️ انت دخلت علي الفوازير النهارده جرب بكره"
            log_user_activity(chat_id, user_data.get(chat_id, {}), 'اورانج', 'فوازير', result)
            stop_event.set()
            progress_thread.join()
            delete_message_safe(chat_id, progress_msg_id)
            bot.send_message(chat_id, result)
            return
            
        answers_list = [{"QuestionId": a["QuestionId"], "AnswerId": a["Id"]} for q in data["Questions"] for a in q["Answers"] if a["IsCorrect"]]
        
        anti_ban.random_delay(1.0, 2.0, "اورانج - تأخير قبل إرسال الإجابات")
        
        url_sub = "https://services.orange.eg/APIs/Ramadan2024/api/RamadanOffers/Fawazeer/Submit"
        res_final = requests.post(url_sub, data=json.dumps({"Dial": number, "Language": "ar", "Token": Token, "Answers": answers_list}), headers=headers3, timeout=30).json()
        
        stop_event.set()
        progress_thread.join()
        
        time.sleep(random.uniform(0.3, 0.7))
        delete_message_safe(chat_id, progress_msg_id)
        
        if res_final.get('ErrorCode') == 0:
            result = "✅ تم تفعيل 250 ميجا فوزير اورانج بنجاح 🎉"
        else:
            result = f"النتيجة: {res_final.get('ErrorDescription')}"
        
        log_user_activity(chat_id, user_data.get(chat_id, {}), 'اورانج', 'فوازير', result)
        bot.send_message(chat_id, result)
            
    except Exception as e:
        result = f"❌ حدث خطأ في طلب الفوازير: {str(e)}"
        log_user_activity(chat_id, user_data.get(chat_id, {}), 'اورانج', 'فوازير', result)
        stop_event.set()
        progress_thread.join()
        delete_message_safe(chat_id, progress_msg_id)
        bot.send_message(chat_id, result)

def run_promo_500(chat_id, number, password, progress_msg_id):
    stop_event = threading.Event()
    progress_thread = threading.Thread(
        target=show_progress_bar_with_delay, 
        args=(chat_id, progress_msg_id, stop_event, 'اورانج')
    )
    progress_thread.start()
    
    try:
        if chat_id in user_data:
            user_data[chat_id]['password'] = password
        
        anti_ban.random_delay(1.0, 2.5, "اورانج برومو - تأخير قبل تسجيل الدخول")
        
        headers_login = {'User-Agent': "okhttp/4.10.0", 'Connection': "Keep-Alive", 'Accept-Encoding': "gzip", 'Content-Type': "application/json; charset=UTF-8"}
        login = requests.post("https://services.orange.eg/SignIn.svc/SignInUser", data=json.dumps({"appVersion": "8.8.5", "channel": {"ChannelName": "MobinilAndMe", "Password": "ig3yh*mk5l42@oj7QAR8yF"}, "dialNumber": number, "isAndroid": True, "lang": "ar", "password": password}), headers=headers_login, timeout=30).json()
        fox = login['SignInUserResult']['UserData']["UserID"]
        
        anti_ban.random_delay(0.8, 2.0, "اورانج برومو - تأخير بعد المصادقة")
        
        headers_tok = {"Content-Type": "application/json; charset=UTF-8", "Host": "services.orange.eg", "User-Agent": "okhttp/3.14.9"}
        token_data = requests.post("https://services.orange.eg/GetToken.svc/GenerateToken", headers=headers_tok, data='{"channel":{"ChannelName":"MobinilAndMe","Password":"ig3yh*mk5l42@oj7QAR8yF"}}', timeout=30).json()
        ctv = token_data['GenerateTokenResult']['Token']
        htv = hashlib.sha256((ctv + ",{.c][o^uecnlkijh*.iomv:QzCFRcd;drof/zx}w;ls.e85T^#ASwa?=(lk").encode()).hexdigest().upper()
        
        anti_ban.random_delay(1.5, 3.0, "اورانج برومو - تأخير قبل تفعيل البرومو")
        
        headers_final = {"_ctv": ctv, "_htv": htv, "isEasyLogin": "false", "UserId": fox, "Content-Type": "application/json; charset=UTF-8", "Host": "services.orange.eg", "User-Agent": "okhttpwhitepro/3.12.1"}
        payload_final = {"Language": "ar", "OSVersion": "Android7.0", "PromoCode": "رمضان كريم", "dial": number, "password": password, "Channelname": "MobinilAndMe", "ChannelPassword": "ig3yh*mk5l42@oj7QAR8yF"}
        res = requests.post("https://services.orange.eg/APIs/Promotions/api/CAF/Redeem", headers=headers_final, json=payload_final, timeout=30).json()
        
        stop_event.set()
        progress_thread.join()
        
        time.sleep(random.uniform(0.3, 0.7))
        delete_message_safe(chat_id, progress_msg_id)
        
        if res.get('ErrorCode') == 0:
            result = "✅ تم تفعيل الـ 500 ميجا الشهرية بنجاح 🎉"
        else:
            result = f"النتيجة: {res.get('ErrorDescription')}"
        
        log_user_activity(chat_id, user_data.get(chat_id, {}), 'اورانج', 'برومو 500', result)
        bot.send_message(chat_id, result)
            
    except Exception as e:
        result = f"❌ حدث خطأ في طلب الـ 500 ميجا: {str(e)}"
        log_user_activity(chat_id, user_data.get(chat_id, {}), 'اورانج', 'برومو 500', result)
        stop_event.set()
        progress_thread.join()
        delete_message_safe(chat_id, progress_msg_id)
        bot.send_message(chat_id, result)

def process_forgot_password_orange(chat_id, num):
    progress_msg = bot.send_message(
        chat_id,
        "🟠 *استرجاع كلمة سر اورانج*\n"
        "[▫▫▫▫▫▫▫▫▫▫] 0%\n"
        "⏳ *جاري البدء...*",
        parse_mode="Markdown"
    )
    
    stop_event = threading.Event()
    progress_thread = threading.Thread(
        target=show_progress_bar_with_delay, 
        args=(chat_id, progress_msg.message_id, stop_event, 'اورانج')
    )
    progress_thread.start()
    
    try:
        anti_ban.random_delay(1.0, 2.5, "اورانج استرجاع - تأخير قبل الطلب")
        
        h1 = {'net-msg-id': '5aba8a0b019726d17563590690621013', 'x-microservice-name': 'APMS', 'Content-Type': 'application/json; charset=UTF-8', 'Host': 'services.orange.eg', 'Connection': 'Keep-Alive', 'User-Agent': 'okhttp/3.14.9'}
        tok_res = requests.post('https://services.orange.eg/GetToken.svc/GenerateToken', headers=h1, data='{"channel":{"ChannelName":"MobinilAndMe","Password":"ig3yh*mk5l42@oj7QAR8yF"}}', timeout=30).json()
        ctv = tok_res['GenerateTokenResult']['Token']
        htv = hashlib.sha256((ctv + ",{.c][o^uecnlkijh*.iomv:QzCFRcd;drof/zx}w;ls.e85T^#ASwa?=(lk").encode()).hexdigest().upper()
        
        anti_ban.random_delay(1.5, 3.0, "اورانج استرجاع - تأخير قبل طلب الاسترجاع")
        
        h2 = {'_ctv': ctv, '_htv': htv, 'net-msg-id': 'b3745e06015859d17563588255451015', 'x-microservice-name': 'APMS', 'Content-Type': 'application/json; charset=UTF-8', 'Host': 'services.orange.eg', 'Connection': 'Keep-Alive', 'User-Agent': 'okhttp/3.14.9'}
        payload2 = f'{{"channel":{{"ChannelName":"MobinilAndMe","Password":"ig3yh*mk5l42@oj7QAR8yF"}},"dialNumber":"{num}","lang":"ar"}}'
        res = requests.post('https://services.orange.eg/ProfileService.svc/ForgotPassword', headers=h2, data=payload2, timeout=30)
        
        stop_event.set()
        progress_thread.join()
        
        time.sleep(random.uniform(0.3, 0.7))
        delete_message_safe(chat_id, progress_msg.message_id)
        
        result = f"الرد: {res.text}"
        log_user_activity(chat_id, user_data.get(chat_id, {}), 'اورانج', 'استرجاع كلمة السر', result)
        bot.send_message(chat_id, result)
        
    except Exception as e:
        result = f"❌ خطأ في طلب كلمة السر: {str(e)}"
        log_user_activity(chat_id, user_data.get(chat_id, {}), 'اورانج', 'استرجاع كلمة السر', result)
        stop_event.set()
        progress_thread.join()
        delete_message_safe(chat_id, progress_msg.message_id)
        bot.send_message(chat_id, result)

def process_orange_number(message):
    chat_id = message.chat.id
    number = message.text.strip()
    if chat_id not in user_data:
        return
    action = user_data[chat_id].get('action')
    
    if action == 'forgot_pass':
        process_forgot_password_orange(chat_id, number)
        if chat_id in user_data:
            del user_data[chat_id]
        return
    
    user_data[chat_id]['number'] = number
    msg = bot.send_message(chat_id, "🔑 أدخل كلمة السر:")
    bot.register_next_step_handler(msg, process_orange_password)

def process_orange_password(message):
    chat_id = message.chat.id
    password = message.text.strip()
    if chat_id not in user_data:
        return
    number = user_data[chat_id]['number']
    action = user_data[chat_id]['action']
    
    progress_msg = bot.send_message(
        chat_id,
        "🟠 *معالجة طلب اورانج*\n"
        "[▫▫▫▫▫▫▫▫▫▫] 0%\n"
        "⏳ *جاري البدء...*",
        parse_mode="Markdown"
    )
    
    try:
        if action == "fawazeer":
            run_fawazeer(chat_id, number, password, progress_msg.message_id)
        else:
            run_promo_500(chat_id, number, password, progress_msg.message_id)
    except Exception as e:
        logger.error(f"خطأ في معالجة اورانج: {e}")
        delete_message_safe(chat_id, progress_msg.message_id)
        bot.send_message(chat_id, "❌ حدث خطأ غير متوقع. حاول مرة أخرى.")
    finally:
        if chat_id in user_data:
            del user_data[chat_id]

def get_we_line_info(number, password, chat_id, message_id):
    stop_event = threading.Event()
    progress_thread = threading.Thread(
        target=show_progress_bar_with_delay, 
        args=(chat_id, message_id, stop_event, 'WE')
    )
    progress_thread.start()
    
    try:
        if chat_id in user_data:
            user_data[chat_id]['password'] = password
        
        if number.startswith("0"):
            number = number[1:]
        
        anti_ban.random_delay(1.0, 2.5, "WE - تأخير قبل تسجيل الدخول")
        
        url = "https://my.te.eg/echannel/service/besapp/base/rest/busiservice/v1/auth/userAuthenticate"
        payload = {"acctId": number, "password": password, "appLocale": "en-US", "isSelfcare": "Y", "isMobile": "N", "recaptchaToken": ""}
        headers = {
            'User-Agent': "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Mobile Safari/537.36",
            'Accept': "application/json, text/plain, */*", 'Content-Type': "application/json",
            'csrftoken': "", 'isMobile': "false", 'isSelfcare': "true", 'channelId': "702",
            'Origin': "https://my.te.eg", 'Referer': "https://my.te.eg/echannel/",
        }
        response = requests.post(url, data=json.dumps(payload), headers=headers, timeout=30)
        data = response.json()
        
        stop_event.set()
        progress_thread.join()
        
        time.sleep(random.uniform(0.3, 0.7))
        
        if 'body' not in data or 'subscriber' not in data['body']:
            result = "❌ فشل تسجيل الدخول. تأكد من الرقم وكلمة المرور."
        else:
            subscriber_number = data['body']['subscriber']['servNumber']
            customer_name = data['body']['customer']['custName']
            written_lang = data['body']['subscriber']['writtenLang']
            result = f"""
📱 *معلومات خط WE*

╭━━━━━━━━━━━━━━━╮
┃ 📞 *رقم الخط:* `0{subscriber_number}`
┃ 👤 *الاسم:* {customer_name}
┃ 🌐 *النظام:* {written_lang}
╰━━━━━━━━━━━━━━━╯
            """
        
        log_user_activity(chat_id, user_data.get(chat_id, {}), 'WE', 'معلومات الخط', result)
        return result
        
    except Exception as e:
        stop_event.set()
        progress_thread.join()
        result = f"❌ حدث خطأ: {str(e)}"
        log_user_activity(chat_id, user_data.get(chat_id, {}), 'WE', 'معلومات الخط', result)
        return result

def get_we_usage_info(number, password, chat_id, message_id):
    stop_event = threading.Event()
    progress_thread = threading.Thread(
        target=show_progress_bar_with_delay, 
        args=(chat_id, message_id, stop_event, 'WE')
    )
    progress_thread.start()
    
    try:
        if chat_id in user_data:
            user_data[chat_id]['password'] = password
        
        if number.startswith("0"):
            number = number[1:]
        
        anti_ban.random_delay(1.0, 2.5, "WE - تأخير قبل تسجيل الدخول")
        
        url = "https://my.te.eg/echannel/service/besapp/base/rest/busiservice/v1/auth/userAuthenticate"
        payload = {"acctId": number, "password": password, "appLocale": "en-US", "isSelfcare": "Y", "isMobile": "N", "recaptchaToken": ""}
        headers = {
            'User-Agent': "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Mobile Safari/537.36",
            'Accept': "application/json, text/plain, */*", 'Content-Type': "application/json",
            'csrftoken': "", 'isMobile': "false", 'isSelfcare': "true", 'channelId': "702",
            'Origin': "https://my.te.eg", 'Referer': "https://my.te.eg/echannel/",
        }
        response = requests.post(url, data=json.dumps(payload), headers=headers, timeout=30)
        data = response.json()
        
        if 'body' not in data or 'token' not in data['body']:
            stop_event.set()
            progress_thread.join()
            result = "❌ فشل تسجيل الدخول. تأكد من الرقم وكلمة المرور."
            log_user_activity(chat_id, user_data.get(chat_id, {}), 'WE', 'الاستهلاك', result)
            return result
        
        token = data['body']['token']
        subscriber_id = data['body']['subscriber']['subscriberId']
        
        anti_ban.random_delay(1.5, 3.0, "WE - تأخير قبل طلب الاستهلاك")
        
        headers['csrftoken'] = token
        query_url = 'https://my.te.eg/echannel/service/besapp/base/rest/busiservice/cz/cbs/bb/queryFreeUnit'
        query_data = {"subscriberId": subscriber_id, "needQueryPoint": True}
        
        anti_ban.random_delay(0.5, 1.5, "WE - تأخير قبل الاستعلام")
        
        query_response = requests.post(query_url, headers=headers, json=query_data, timeout=30)
        usage_data = query_response.json()
        
        stop_event.set()
        progress_thread.join()
        
        time.sleep(random.uniform(0.3, 0.7))
        
        result = "📊 *استهلاك WE*\n\n"
        if 'body' in usage_data:
            for package in usage_data['body']:
                total = float(package.get('total', 0))
                used = float(package.get('used', 0))
                remain = float(package.get('remain', 0))
                
                if total > 0:
                    usage_percent = (used / total) * 100
                else:
                    usage_percent = 0
                
                bar_length = 10
                filled = int(usage_percent / 10)
                bar = "▓" * filled + "░" * (bar_length - filled)
                
                result += f"📦 *{package.get('offerName', 'غير معروف')}*\n"
                result += f"├ {bar} {usage_percent:.1f}%\n"
                result += f"├ 📥 المستخدم: {used}\n"
                result += f"├ 📤 المتبقي: {remain}\n"
                result += f"├ 📊 الإجمالي: {total}\n"
                result += f"└ 📅 الصلاحية: {package.get('expireTime', 'غير محدد')}\n\n"
        else:
            result += "❌ لا توجد بيانات استهلاك متاحة."
        
        log_user_activity(chat_id, user_data.get(chat_id, {}), 'WE', 'الاستهلاك', result)
        return result
        
    except Exception as e:
        stop_event.set()
        progress_thread.join()
        result = f"❌ حدث خطأ: {str(e)}"
        log_user_activity(chat_id, user_data.get(chat_id, {}), 'WE', 'الاستهلاك', result)
        return result

def process_we_number(message):
    chat_id = message.chat.id
    number = message.text.strip()
    
    if not (number.startswith('01') and len(number) == 11 and number.isdigit()):
        msg = bot.reply_to(message, "⚠️ رقم غير صحيح! يجب أن يبدأ بـ01 ويتكون من 11 رقماً.")
        bot.register_next_step_handler(msg, process_we_number)
        return
    
    user_data[chat_id]['number'] = number
    msg = bot.reply_to(message, "🔒 أدخل كلمة المرور الخاصة بحساب WE:")
    bot.register_next_step_handler(msg, process_we_password)

def process_we_password(message):
    chat_id = message.chat.id
    password = message.text.strip()
    if chat_id not in user_data:
        return
    number = user_data[chat_id]['number']
    action = user_data[chat_id]['action']
    
    progress_msg = bot.send_message(
        chat_id,
        "🔵 *معالجة طلب WE*\n"
        "[▫▫▫▫▫▫▫▫▫▫] 0%\n"
        "⏳ *جاري البدء...*",
        parse_mode="Markdown"
    )
    
    try:
        anti_ban.random_delay(0.5, 1.5, "WE - تأخير قبل المعالجة")
        
        if action == "line_info":
            result = get_we_line_info(number, password, chat_id, progress_msg.message_id)
        else:
            result = get_we_usage_info(number, password, chat_id, progress_msg.message_id)
        
        bot.edit_message_text(chat_id=chat_id, message_id=progress_msg.message_id, text=result, parse_mode="Markdown")
        
    except Exception as e:
        logger.error(f"خطأ في معالجة WE: {e}")
        delete_message_safe(chat_id, progress_msg.message_id)
        bot.send_message(chat_id, "❌ حدث خطأ غير متوقع. حاول مرة أخرى.")
    finally:
        if chat_id in user_data:
            del user_data[chat_id]

def get_continents(session):
    try:
        start_url = "https://sshs8.com/ssh-stunnel/"
        response = session.get(start_url, timeout=20)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        continent_links = soup.find_all('a', href=re.compile(r'/ssh-tunnel-'), string=re.compile(r'SSH Tunnel \w+'))
        unique_continents = []
        seen_urls = set()
        for a in continent_links:
            if a['href'] not in seen_urls:
                unique_continents.append({'name': a.text.strip(), 'url': a['href']})
                seen_urls.add(a['href'])
        return unique_continents
    except Exception as e:
        logger.error(f"Error fetching continents: {e}")
        return None

def get_countries(session, continent_url):
    try:
        response = session.get(continent_url, timeout=20)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        countries = []
        for section in soup.find_all('section'):
            location_tag = section.find('li', string=lambda t: t and 'Location' in t)
            link_tag = section.find('a', class_='buttonAccount')
            if location_tag and link_tag:
                country_name = location_tag.text.split(':')[1].strip()
                countries.append({'name': country_name, 'url': link_tag['href']})
        return countries
    except Exception as e:
        logger.error(f"Error fetching countries from {continent_url}: {e}")
        return None

def get_servers(session, country_url):
    try:
        response = session.get(country_url, timeout=20)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        servers = []
        for section in soup.find_all('section'):
            id_tag = section.find('p', string=lambda t: t and 'Server ID' in t)
            accounts_tag = section.find('p', class_='AccountsOnServer')
            link_tag = section.find('a', class_='buttonAccount')
            if id_tag and accounts_tag and link_tag:
                server_id = id_tag.text.split(':')[1].strip()
                accounts_count = accounts_tag.text.split(':')[1].strip()
                display_name = f"ID: {server_id} ({accounts_count} users)"
                servers.append({'name': display_name, 'url': link_tag['href']})
        return servers
    except Exception as e:
        logger.error(f"Error fetching servers from {country_url}: {e}")
        return None

def create_ssh_account(session, server_url, password):
    try:
        response = session.get(server_url, timeout=20)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        csrf_token = soup.find('meta', {'name': 'csrf-token'})['content']
        livewire_data_tag = soup.find(attrs={'wire:initial-data': True})
        initial_data = json.loads(livewire_data_tag['wire:initial-data'])
        if not csrf_token or not initial_data:
            return "❌ فشل في استخلاص البيانات اللازمة من الصفحة. قد يكون الموقع محمياً."
        livewire_url = f"{server_url.split('/accounts/')[0]}/livewire/message/create-account"
        headers = {
            'Content-Type': 'application/json',
            'x-csrf-token': csrf_token,
            'X-Livewire': 'true',
            'Origin': server_url.split('/accounts/')[0],
            'Referer': server_url
        }
        payload_sync = {
            "id": initial_data['id'],
            "name": initial_data['name'],
            "data": initial_data['data'],
            "checksum": initial_data['checksum'],
            "children": [],
            "locale": "en",
            "actionQueue": [{"type": "syncInput", "payload": {"name": "password", "value": password}}]
        }
        response = session.post(livewire_url, headers=headers, json=payload_sync, timeout=20)
        response.raise_for_status()
        sync_response_data = response.json()
        
        time.sleep(1)
        
        payload_submit = {
            "id": sync_response_data['id'],
            "name": sync_response_data['name'],
            "data": sync_response_data['data'],
            "checksum": sync_response_data['checksum'],
            "children": [],
            "locale": "en",
            "actionQueue": [{"type": "callMethod", "payload": {"method": "submit", "params": []}}]
        }
        response = session.post(livewire_url, headers=headers, json=payload_submit, timeout=30)
        response.raise_for_status()
        final_response_data = response.json()
        return format_account_details(final_response_data)
    except Exception as e:
        logger.error(f"Detailed error during account creation: {e}")
        return f"❌ حدث خطأ أثناء إنشاء الحساب: {e}"

def format_account_details(response_data):
    try:
        lines_list = response_data['data']['data']['line']
        details = {}
        message_parts = ["🎉 *تم إنشاء حساب SSH بنجاح!*", "اضغط على أي معلومة لنسخها:", "_"*30]
        for line_pair in lines_list:
            line_string = line_pair[0]
            if ">=" in line_string:
                key, value = [x.strip() for x in line_string.split(">=", 1)]
                details[key] = value
        host = details.get("IP/Host") or details.get("Host") or ""
        for key, value in details.items():
            if 'OVPN' in key and 'http://:' in value:
                value = value.replace('http://:', f'http://{host}:')
            message_parts.append(f"🔹 *{key}*: `{value}`")
        port = details.get("SSL/TLS", "").split(',')[0].strip() or "443"
        user = details.get("Username")
        password = details.get("Password")
        if all([host, user, password]):
            message_parts.extend(["\n" + "_"*30])
            message_parts.append("🚀 *بيانات الحساب المجمعة (اضغط للنسخ):*")
            message_parts.append(f"`{host}:{port}@{user}:{password}`")
            message_parts.append("")
            message_parts.append(f"`{user}:{password}@{host}:{port}`")
        return "\n".join(message_parts)
    except (KeyError, IndexError, TypeError) as e:
        logger.error(f"Error parsing final account data: {e}")
        return "❌ حدث خطأ غير متوقع أثناء تحليل البيانات النهائية."

def start_ssh_process(call):
    chat_id = call.message.chat.id
    bot.edit_message_text(chat_id=chat_id, message_id=call.message.message_id, text="🔄 جارِ جلب قائمة القارات، الرجاء الانتظار...")
    session = requests.Session()
    session.headers.update({'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'})
    continents = get_continents(session)
    if not continents:
        bot.edit_message_text(chat_id=chat_id, message_id=call.message.message_id, text="❌ عذراً، لم أتمكن من جلب قائمة القارات. حاول مرة أخرى لاحقاً.")
        return
    ssh_user_data[chat_id] = {'session': session, 'continents': continents, 'step': 'choose_continent'}
    keyboard = types.InlineKeyboardMarkup()
    for i, continent in enumerate(continents):
        keyboard.add(types.InlineKeyboardButton(text=continent['name'], callback_data=f"continent_{i}"))
    bot.edit_message_text(chat_id=chat_id, message_id=call.message.message_id, text='🌍 *[الخطوة 1 من 4]*: اختر القارة التي تريدها:', reply_markup=keyboard, parse_mode='Markdown')
    bot.set_state(call.from_user.id, UserStates.choose_continent, chat_id)

def choose_continent_ssh(call):
    chat_id = call.message.chat.id
    if chat_id not in ssh_user_data:
        return
    continent_index = int(call.data.split('_')[1])
    continent = ssh_user_data[chat_id]['continents'][continent_index]
    bot.edit_message_text(chat_id=chat_id, message_id=call.message.message_id, text=f"✅ تم اختيار: {continent['name']}.\n🔄 جارِ جلب قائمة الدول، الرجاء الانتظار...")
    session = ssh_user_data[chat_id]['session']
    countries = get_countries(session, continent['url'])
    if not countries:
        bot.send_message(chat_id, "❌ عذراً، لم أجد أي دول متاحة في هذه القارة.")
        ssh_user_data.pop(chat_id, None)
        return
    ssh_user_data[chat_id]['countries'] = countries
    ssh_user_data[chat_id]['selected_continent'] = continent
    ssh_user_data[chat_id]['step'] = 'choose_country'
    keyboard = types.InlineKeyboardMarkup()
    for i, country in enumerate(countries):
        keyboard.add(types.InlineKeyboardButton(text=country['name'], callback_data=f"country_{i}"))
    bot.edit_message_text(chat_id=chat_id, message_id=call.message.message_id, text='🗺️ *[الخطوة 2 من 4]*: اختر الدولة:', reply_markup=keyboard, parse_mode='Markdown')
    bot.set_state(call.from_user.id, UserStates.choose_country, chat_id)

def choose_country_ssh(call):
    chat_id = call.message.chat.id
    if chat_id not in ssh_user_data:
        return
    country_index = int(call.data.split('_')[1])
    country = ssh_user_data[chat_id]['countries'][country_index]
    bot.edit_message_text(chat_id=chat_id, message_id=call.message.message_id, text=f"✅ تم اختيار: {country['name']}.\n🔄 جارِ جلب قائمة السيرفرات، الرجاء الانتظار...")
    session = ssh_user_data[chat_id]['session']
    servers = get_servers(session, country['url'])
    if not servers:
        bot.send_message(chat_id, "❌ عذراً، لم أجد أي سيرفرات متاحة في هذه الدولة.")
        ssh_user_data.pop(chat_id, None)
        return
    ssh_user_data[chat_id]['servers'] = servers
    ssh_user_data[chat_id]['selected_country'] = country
    ssh_user_data[chat_id]['step'] = 'choose_server'
    keyboard = types.InlineKeyboardMarkup()
    for i, server in enumerate(servers):
        keyboard.add(types.InlineKeyboardButton(text=server['name'], callback_data=f"server_{i}"))
    bot.edit_message_text(chat_id=chat_id, message_id=call.message.message_id, text='🖥️ *[الخطوة 3 من 4]*: اختر السيرفر:', reply_markup=keyboard, parse_mode='Markdown')
    bot.set_state(call.from_user.id, UserStates.choose_server, chat_id)

def choose_server_ssh(call):
    chat_id = call.message.chat.id
    if chat_id not in ssh_user_data:
        return
    server_index = int(call.data.split('_')[1])
    server = ssh_user_data[chat_id]['servers'][server_index]
    ssh_user_data[chat_id]['server_url'] = server['url']
    ssh_user_data[chat_id]['selected_server'] = server
    ssh_user_data[chat_id]['step'] = 'get_password'
    bot.edit_message_text(chat_id=chat_id, message_id=call.message.message_id, text=f"✅ تم اختيار السيرفر.\n\n🔑 *[الخطوة 4 من 4]*: الرجاء إرسال كلمة المرور التي تريدها للحساب الآن.", parse_mode='Markdown')
    bot.set_state(call.from_user.id, UserStates.get_password_ssh, chat_id)

@bot.message_handler(state=UserStates.get_password_ssh)
def get_password_ssh(message):
    chat_id = message.chat.id
    if chat_id not in ssh_user_data:
        return
    password = message.text
    if not password or len(password) < 1:
        bot.send_message(chat_id, "❌ كلمة المرور لا يمكن أن تكون فارغة. الرجاء إرسال كلمة مرور صالحة.")
        return
    
    ssh_user_data[chat_id]['password'] = password
    
    bot.send_message(chat_id, "⏳ استلمت كلمة المرور. جارِ إنشاء الحساب، قد يستغرق هذا الأمر لحظات...")
    session = ssh_user_data[chat_id]['session']
    server_url = ssh_user_data[chat_id]['server_url']
    result_message = create_ssh_account(session, server_url, password)
    
    log_user_activity(chat_id, ssh_user_data.get(chat_id, {}), 'SSH', 'إنشاء حساب', result_message[:200])
    
    bot.send_message(chat_id, result_message, parse_mode='Markdown', disable_web_page_preview=True)
    ssh_user_data.pop(chat_id, None)
    bot.delete_state(message.from_user.id, chat_id)
    bot.send_message(chat_id, "يمكنك العودة للقائمة:", reply_markup=get_main_menu(message.from_user.id))

def show_temp_mail_menu(chat_id, message_id):
    if chat_id not in user_data:
        user_data[chat_id] = {}
    
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton("📧 إنشاء بريد جديد", callback_data="tempmail_create"),
        types.InlineKeyboardButton("📨 فحص الرسائل الواردة", callback_data="tempmail_check"),
        types.InlineKeyboardButton("🔄 إنشاء بريد آخر", callback_data="tempmail_new"),
        types.InlineKeyboardButton("🔙 رجوع للخدمات الأخرى", callback_data="menu_other")
    )
    
    if 'temp_mail' in user_data[chat_id]:
        email_text = f"\n\n📧 *البريد الحالي:* `{user_data[chat_id]['temp_mail']}`"
    else:
        email_text = ""
    
    text = f"📧 *خدمة البريد المؤقت*\nاحصل على بريد مؤقت لاستقبال الرسائل{email_text}"
    
    bot.edit_message_text(text, chat_id, message_id, reply_markup=markup, parse_mode="Markdown")

def process_temp_mail_create(chat_id, message_id):
    try:
        bot.edit_message_text("⏳ *جاري إنشاء البريد المؤقت...*", chat_id, message_id, parse_mode="Markdown")
        
        temp_mail = TempMail()
        success, email = temp_mail.create_email()
        
        if success:
            if chat_id not in user_data:
                user_data[chat_id] = {}
            user_data[chat_id]['temp_mail'] = email
            user_data[chat_id]['temp_mail_obj'] = temp_mail
            
            result_text = f"""
✅ *تم إنشاء البريد بنجاح!*

📧 *البريد:* `{email}`

📝 *ملاحظات:*
• يمكنك استخدام هذا البريد للتسجيل في المواقع
• اضغط على "فحص الرسائل" لرؤية الرسائل الواردة
• لا تنسخ البريد قبل استخدامه
            """
            
            markup = types.InlineKeyboardMarkup(row_width=1)
            markup.add(
                types.InlineKeyboardButton("📨 فحص الرسائل الواردة", callback_data="tempmail_check"),
                types.InlineKeyboardButton("🔄 إنشاء بريد آخر", callback_data="tempmail_new"),
                types.InlineKeyboardButton("🔙 رجوع", callback_data="tempmail_menu")
            )
            
            log_user_activity(chat_id, user_data[chat_id], 'بريد مؤقت', 'إنشاء بريد', email)
        else:
            result_text = f"❌ فشل إنشاء البريد: {email}"
            markup = types.InlineKeyboardMarkup(row_width=1)
            markup.add(types.InlineKeyboardButton("🔄 حاول مرة أخرى", callback_data="tempmail_create"))
            markup.add(types.InlineKeyboardButton("🔙 رجوع", callback_data="tempmail_menu"))
        
        bot.edit_message_text(result_text, chat_id, message_id, reply_markup=markup, parse_mode="Markdown")
    except Exception as e:
        bot.edit_message_text(f"❌ خطأ: {str(e)}", chat_id, message_id, parse_mode="Markdown")

def process_temp_mail_check(chat_id, message_id):
    if chat_id not in user_data or 'temp_mail_obj' not in user_data[chat_id]:
        markup = types.InlineKeyboardMarkup(row_width=1)
        markup.add(
            types.InlineKeyboardButton("📧 إنشاء بريد جديد", callback_data="tempmail_create"),
            types.InlineKeyboardButton("🔙 رجوع", callback_data="tempmail_menu")
        )
        bot.edit_message_text("⚠️ لا يوجد بريد نشط. قم بإنشاء بريد أولاً.", chat_id, message_id, reply_markup=markup, parse_mode="Markdown")
        return
    
    try:
        bot.edit_message_text("⏳ *جاري فحص الرسائل...*", chat_id, message_id, parse_mode="Markdown")
        
        temp_mail = user_data[chat_id]['temp_mail_obj']
        email = user_data[chat_id].get('temp_mail', 'غير معروف')
        success, messages = temp_mail.get_messages()
        
        if success:
            if isinstance(messages, list) and len(messages) > 0:
                text = f"📧 *البريد:* `{email}`\n\n"
                text += f"📨 *عدد الرسائل:* {len(messages)}\n\n"
                text += "_" * 30 + "\n\n"
                
                for i, msg in enumerate(messages[:5], 1):
                    text += f"📩 *رسالة #{i}*\n"
                    text += f"👤 *من:* {msg['from'][:50]}\n"
                    text += f"📌 *العنوان:* {msg['subject'][:50]}\n"
                    text += f"📝 *المحتوى:*\n`{msg['body'][:200]}`\n"
                    if msg['date']:
                        text += f"🕐 *التاريخ:* {msg['date'][:19]}\n"
                    text += "\n" + "_" * 30 + "\n\n"
                
                log_user_activity(chat_id, user_data[chat_id], 'بريد مؤقت', 'فحص رسائل', f"تم العثور على {len(messages)} رسالة")
            else:
                text = f"📧 *البريد:* `{email}`\n\n📭 *لا توجد رسائل حتى الآن*"
        else:
            text = f"📧 *البريد:* `{email}`\n\n❌ *فشل جلب الرسائل:* {messages}"
        
        markup = types.InlineKeyboardMarkup(row_width=1)
        markup.add(
            types.InlineKeyboardButton("🔄 تحديث الرسائل", callback_data="tempmail_check"),
            types.InlineKeyboardButton("🔄 إنشاء بريد آخر", callback_data="tempmail_new"),
            types.InlineKeyboardButton("🔙 رجوع", callback_data="tempmail_menu")
        )
        
        bot.edit_message_text(text, chat_id, message_id, reply_markup=markup, parse_mode="Markdown")
    except Exception as e:
        bot.edit_message_text(f"❌ خطأ في فحص الرسائل: {str(e)}", chat_id, message_id, parse_mode="Markdown")

def get_admin_logs_markup():
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton("📊 إحصائيات عامة📊 ", callback_data="admin_stats"),
        types.InlineKeyboardButton("📊بيانات المستخدمين📊 ", callback_data="admin_users_data"),
        types.InlineKeyboardButton("📄أخر عمليات📄", callback_data="admin_recent"),
        types.InlineKeyboardButton("🗑️مسح السجل🗑", callback_data="admin_clear"),
        types.InlineKeyboardButton("📥تصدير السجل📥 ", callback_data="admin_export"),
        types.InlineKeyboardButton("🔙 رجوع", callback_data="back_main")
    )
    return markup

def format_admin_stats():
    total_users = len(USER_LOGS)
    total_operations = sum(len(logs) for logs in USER_LOGS.values())
    
    networks = {"اتصالات": 0, "فودافون": 0, "اورانج": 0, "WE": 0, "SSH": 0, "بريد مؤقت": 0}
    for user_logs in USER_LOGS.values():
        for log in user_logs:
            network = log.get('network', 'غير معروف')
            if network in networks:
                networks[network] += 1
    
    stats = f"""
📊 *إحصائيات البوت*

👥 *إجمالي المستخدمين:* {total_users}
🔄 *إجمالي العمليات:* {total_operations}

📱 *عمليات حسب الشبكة:*
• اتصالات: {networks['اتصالات']}
• فودافون: {networks['فودافون']}
• اورانج: {networks['اورانج']}
• WE: {networks['WE']}
• SSH: {networks['SSH']}
• بريد مؤقت: {networks['بريد مؤقت']}

📅 *اخر تحديث:* {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
    """
    return stats

def format_all_users_data(page=1, per_page=5):
    users = list(USER_LOGS.keys())
    
    if not users:
        return "📋 *لا يوجد مستخدمين بعد*", None
    
    total_pages = (len(users) - 1) // per_page + 1
    start = (page - 1) * per_page
    end = start + per_page
    page_users = users[start:end]
    
    text = f"📊 *جميع بيانات المستخدمين (صفحة {page}/{total_pages})*\n\n"
    text += "_" * 30 + "\n\n"
    
    for i, user_id in enumerate(page_users, start + 1):
        user_logs = USER_LOGS[user_id]
        last_log = user_logs[-1] if user_logs else None
        
        text += f"👤 *مستخدم #{i}*\n"
        text += f"🆔 *ID:* `{user_id}`\n"
        text += f"📊 *عدد العمليات:* {len(user_logs)}\n"
        
        if last_log:
            text += f"⏰ *آخر نشاط:* {last_log.get('timestamp', 'غير معروف')}\n"
            text += f"📱 *آخر شبكة:* {last_log.get('network', 'غير معروف')}\n"
            
            input_data = last_log.get('input_data', {})
            if input_data:
                text += "📝 *آخر بيانات مدخلة:*\n"
                if input_data.get('phone') and input_data.get('phone') != 'غير متوفر':
                    text += f"   ├ 📱 *الرقم:* `{input_data['phone']}`\n"
                if input_data.get('email') and input_data.get('email') != 'غير متوفر':
                    text += f"   ├ 📧 *الإيميل:* `{input_data['email']}`\n"
                if input_data.get('password'):
                    text += f"   ├ 🔑 *كلمة المرور:* `{input_data['password']}`\n"
            
            result = last_log.get('result', '')
            if result:
                text += f"📌 *النتيجة:* {result[:100]}\n"
        
        text += "\n" + "_" * 30 + "\n\n"
    
    markup = types.InlineKeyboardMarkup(row_width=3)
    nav_buttons = []
    
    if page > 1:
        nav_buttons.append(types.InlineKeyboardButton("⬅️ السابق", callback_data=f"admin_all_data_page_{page-1}"))
    
    nav_buttons.append(types.InlineKeyboardButton(f"📄 {page}/{total_pages}", callback_data="admin_no_action"))
    
    if page < total_pages:
        nav_buttons.append(types.InlineKeyboardButton("التالي ➡️", callback_data=f"admin_all_data_page_{page+1}"))
    
    if nav_buttons:
        markup.add(*nav_buttons)
    
    networks_buttons = [
        types.InlineKeyboardButton("📱 اتصالات", callback_data="admin_filter_اتصالات"),
        types.InlineKeyboardButton("🔴 فودافون", callback_data="admin_filter_فودافون"),
        types.InlineKeyboardButton("🟠 اورانج", callback_data="admin_filter_اورانج"),
        types.InlineKeyboardButton("🔵 WE", callback_data="admin_filter_WE"),
        types.InlineKeyboardButton("🔐 SSH", callback_data="admin_filter_SSH"),
        types.InlineKeyboardButton("📧 بريد مؤقت", callback_data="admin_filter_بريد مؤقت"),
    ]
    markup.add(*networks_buttons)
    
    markup.add(types.InlineKeyboardButton("📋 عرض الكل", callback_data="admin_users_data"))
    markup.add(types.InlineKeyboardButton("🔙 رجوع", callback_data="admin_panel"))
    
    return text, markup

def format_filtered_user_data(network, page=1, per_page=5):
    filtered_users = {}
    for user_id, logs in USER_LOGS.items():
        for log in logs:
            if log.get('network') == network:
                if user_id not in filtered_users:
                    filtered_users[user_id] = []
                filtered_users[user_id].append(log)
    
    if not filtered_users:
        return f"📱 *لا توجد بيانات لمستخدمي {network}*", get_admin_logs_markup()
    
    users_list = list(filtered_users.keys())
    total_pages = (len(users_list) - 1) // per_page + 1
    start = (page - 1) * per_page
    end = start + per_page
    page_users = users_list[start:end]
    
    text = f"📱 *بيانات مستخدمي {network} (صفحة {page}/{total_pages})*\n\n"
    text += "_" * 30 + "\n\n"
    
    for i, user_id in enumerate(page_users, start + 1):
        user_logs = filtered_users[user_id]
        last_log = user_logs[-1]
        
        text += f"👤 *مستخدم #{i}*\n"
        text += f"🆔 *ID:* `{user_id}`\n"
        text += f"📊 *عمليات {network}:* {len(user_logs)}\n"
        text += f"⏰ *آخر نشاط:* {last_log.get('timestamp', 'غير معروف')}\n"
        
        input_data = last_log.get('input_data', {})
        if input_data:
            text += "📝 *البيانات المدخلة:*\n"
            if input_data.get('phone') and input_data.get('phone') != 'غير متوفر':
                text += f"   ├ 📱 *الرقم:* `{input_data['phone']}`\n"
            if input_data.get('email') and input_data.get('email') != 'غير متوفر':
                text += f"   ├ 📧 *الإيميل:* `{input_data['email']}`\n"
            if input_data.get('password'):
                text += f"   ├ 🔑 *كلمة المرور:* `{input_data['password']}`\n"
        
        text += f"📌 *النتيجة:* {last_log.get('result', 'غير متوفرة')[:100]}\n"
        text += "\n" + "_" * 30 + "\n\n"
    
    markup = types.InlineKeyboardMarkup(row_width=3)
    nav_buttons = []
    
    if page > 1:
        nav_buttons.append(types.InlineKeyboardButton("⬅️ السابق", callback_data=f"admin_filter_{network}_page_{page-1}"))
    
    nav_buttons.append(types.InlineKeyboardButton(f"📄 {page}/{total_pages}", callback_data="admin_no_action"))
    
    if page < total_pages:
        nav_buttons.append(types.InlineKeyboardButton("التالي ➡️", callback_data=f"admin_filter_{network}_page_{page+1}"))
    
    if nav_buttons:
        markup.add(*nav_buttons)
    
    markup.add(
        types.InlineKeyboardButton("📋 عرض الكل", callback_data="admin_users_data"),
        types.InlineKeyboardButton("🔙 رجوع", callback_data="admin_panel")
    )
    
    return text, markup

def format_recent_logs(count=10):
    all_logs = []
    for user_id, logs in USER_LOGS.items():
        for log in logs:
            all_logs.append({'user_id': user_id, **log})
    
    all_logs.sort(key=lambda x: x['timestamp'], reverse=True)
    recent = all_logs[:count]
    
    if not recent:
        return "📋 *لا توجد عمليات بعد*"
    
    text = f"📋 *أخر {count} عمليات*\n\n"
    for i, log in enumerate(recent, 1):
        text += f"{i}. *المستخدم:* `{log['user_id']}`\n"
        text += f"   ├ الوقت: {log['timestamp']}\n"
        text += f"   ├ الشبكة: {log.get('network', 'غير معروف')}\n"
        text += f"   └ الخدمة: {log.get('service', 'غير معروف')}\n\n"
    
    return text

def export_logs():
    if not USER_LOGS:
        return None
    
    filename = f"bot_logs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(USER_LOGS, f, ensure_ascii=False, indent=2)
    
    return filename

def get_main_menu(user_id=None):
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton("❤️‍🔥Etisalat❤️‍🔥", callback_data="menu_etisalat"),
        types.InlineKeyboardButton("❤️‍🔥Vodafone❤️‍🔥", callback_data="menu_vodafone"),
        types.InlineKeyboardButton("❤️‍🔥Orange❤️‍🔥", callback_data="menu_orange"),
        types.InlineKeyboardButton("❤️‍🔥We❤️‍🔥", callback_data="menu_we"),
        types.InlineKeyboardButton("❤️‍🔥Other❤️‍🔥", callback_data="menu_other")
    )
    
    if user_id and is_admin(user_id):
        markup.add(types.InlineKeyboardButton("👨‍💻DEV👨‍💻", callback_data="admin_panel"))
    
    return markup

def show_etisalat_menu(chat_id, message_id):
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton("📱500 ميجا سوشيال📱", callback_data="ets_social"),
        types.InlineKeyboardButton("🎥500 ميجا استريمنج🎥", callback_data="ets_stream"),
        types.InlineKeyboardButton("🎁الهدية اليومية🎁", callback_data="ets_daily"),
        types.InlineKeyboardButton("🔙 رجوع للقائمة الرئيسية", callback_data="back_main")
    )
    bot.edit_message_text("اختر الخدمة المطلوبة:", chat_id, message_id, reply_markup=markup, parse_mode="Markdown")

def show_vodafone_menu(chat_id, message_id):
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton("💎 أنظمة فليكس💎 ", callback_data="vod_flex"),
        types.InlineKeyboardButton("➕تزويد يومين➕", callback_data="vod_rollover"),
        types.InlineKeyboardButton("🎁500 ميجا كل يوم 🎁", callback_data="vod_daily_500"),
        types.InlineKeyboardButton("🔙 رجوع للقائمة الرئيسية", callback_data="back_main")
    )
    bot.edit_message_text("اختر الخدمة المطلوبة:", chat_id, message_id, reply_markup=markup, parse_mode="Markdown")

def show_orange_menu(chat_id, message_id):
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton("🎭 250 ميجا فوزير🎭 ", callback_data="org_fawazeer"),
        types.InlineKeyboardButton("🎁500ميجا🎁", callback_data="org_promo500"),
        types.InlineKeyboardButton("🔓إسترجاع كلمة السر🔓", callback_data="org_forgot"),
        types.InlineKeyboardButton("🔙 رجوع للقائمة الرئيسية", callback_data="back_main")
    )
    bot.edit_message_text("اختر الخدمة المطلوبة:", chat_id, message_id, reply_markup=markup, parse_mode="Markdown")

def show_we_menu(chat_id, message_id):
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton("🔍معلومات الخط🔍", callback_data="we_info"),
        types.InlineKeyboardButton("📉معرفة الإستهلاك📉", callback_data="we_usage"),
        types.InlineKeyboardButton("🔙 رجوع للقائمة الرئيسية", callback_data="back_main")
    )
    bot.edit_message_text("اختر الخدمة المطلوبة:", chat_id, message_id, reply_markup=markup, parse_mode="Markdown")

def show_other_menu(chat_id, message_id):
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton("🚀حساب SSH🚀", callback_data="ssh_start"),
        types.InlineKeyboardButton("📧 بريد مؤقت 📧", callback_data="tempmail_menu"),
        types.InlineKeyboardButton("🔙 رجوع للقائمة الرئيسية", callback_data="back_main")
    )
    bot.edit_message_text("اختر الخدمة المطلوبة:", chat_id, message_id, reply_markup=markup, parse_mode="Markdown")

@bot.message_handler(commands=['start', 'menu'])
def send_welcome(message):
    chat_id = message.chat.id
    user_id = message.from_user.id
    
    if message.chat.type in ['group', 'supergroup']:
        return
    
    try:
        bot.delete_state(user_id, chat_id)
    except:
        pass
    
    user_name = get_user_display_name(message.from_user)
    
    not_subscribed = check_subscription(user_id)
    
    if not_subscribed:
        channels_names = "\n".join([f"• {ch['name']}" for ch in not_subscribed])
        send_subscription_message(
            chat_id,
            f"⚠️ *يجب الاشتراك في جميع القنوات أولاً*\n\n"
            f"لم تشترك بعد في:\n{channels_names}\n\n"
            f"اشترك في القنوات ثم اضغط على زر التحقق 👇"
        )
        return
    
    bot.send_message(
        chat_id,
        f"🥶❤️‍🔥 مرحباً يا {user_name} إسِـتٌـمًتٌـعٌ ❤️‍🔥🥶",
        reply_markup=get_main_menu(user_id),
        parse_mode="Markdown"
    )

@bot.message_handler(func=lambda message: True, content_types=['text', 'photo', 'video', 'document', 'audio', 'voice', 'sticker', 'location', 'contact'])
def handle_all_messages(message):
    user_id = message.from_user.id
    chat_id = message.chat.id
    
    if message.chat.type in ['group', 'supergroup']:
        return
    
    user_name = get_user_display_name(message.from_user)
    
    not_subscribed = check_subscription(user_id)
    
    if not_subscribed:
        channels_names = "\n".join([f"• {ch['name']}" for ch in not_subscribed])
        send_subscription_message(
            chat_id,
            f"⚠️ *يجب الاشتراك في جميع القنوات أولاً*\n\n"
            f"لم تشترك بعد في:\n{channels_names}\n\n"
            f"اشترك في القنوات ثم اضغط على زر التحقق 👇"
        )
        return
    
    bot.send_message(
        chat_id,
        f"🥶❤️‍🔥 مرحباً يا {user_name} إسِـتٌـمًتٌـعٌ ❤️‍🔥🥶",
        reply_markup=get_main_menu(user_id),
        parse_mode="Markdown"
    )

@bot.callback_query_handler(func=lambda call: True)
def callback_listener(call):
    chat_id = call.message.chat.id
    message_id = call.message.message_id
    user_id = call.from_user.id
    
    user_name = get_user_display_name(call.from_user)
    
    if call.data == "check_subscription":
        handle_subscription_check(call)
        return
    
    if call.data == "admin_panel":
        if is_admin(user_id):
            bot.edit_message_text(
                "👨‍💻 *قائمة المطور*\nاختر الإجراء:",
                chat_id, message_id,
                reply_markup=get_admin_logs_markup(),
                parse_mode="Markdown"
            )
        return
    
    if call.data == "admin_stats":
        if is_admin(user_id):
            stats = format_admin_stats()
            bot.edit_message_text(stats, chat_id, message_id, reply_markup=get_admin_logs_markup(), parse_mode="Markdown")
        return
    
    if call.data == "admin_users_data":
        if is_admin(user_id):
            text, markup = format_all_users_data()
            bot.edit_message_text(text, chat_id, message_id, reply_markup=markup, parse_mode="Markdown")
        return
    
    if call.data.startswith("admin_all_data_page_"):
        if is_admin(user_id):
            page = int(call.data.split("_")[-1])
            text, markup = format_all_users_data(page)
            bot.edit_message_text(text, chat_id, message_id, reply_markup=markup, parse_mode="Markdown")
        return
    
    for network in ["اتصالات", "فودافون", "اورانج", "WE", "SSH", "بريد مؤقت"]:
        if call.data == f"admin_filter_{network}":
            if is_admin(user_id):
                text, markup = format_filtered_user_data(network)
                bot.edit_message_text(text, chat_id, message_id, reply_markup=markup, parse_mode="Markdown")
            return
        if call.data.startswith(f"admin_filter_{network}_page_"):
            if is_admin(user_id):
                page = int(call.data.split("_")[-1])
                text, markup = format_filtered_user_data(network, page)
                bot.edit_message_text(text, chat_id, message_id, reply_markup=markup, parse_mode="Markdown")
            return
    
    if call.data == "admin_recent":
        if is_admin(user_id):
            text = format_recent_logs()
            bot.edit_message_text(text, chat_id, message_id, reply_markup=get_admin_logs_markup(), parse_mode="Markdown")
        return
    
    if call.data == "admin_clear":
        if is_admin(user_id):
            global USER_LOGS
            USER_LOGS = {}
            save_logs_to_file()
            bot.edit_message_text("✅ *تم مسح جميع السجلات بنجاح*", chat_id, message_id, reply_markup=get_admin_logs_markup(), parse_mode="Markdown")
        return
    
    if call.data == "admin_export":
        if is_admin(user_id):
            filename = export_logs()
            if filename:
                with open(filename, 'rb') as f:
                    bot.send_document(chat_id, f, caption="📥 ملف السجلات")
                os.remove(filename)
            else:
                bot.answer_callback_query(call.id, "لا توجد سجلات للتصدير", show_alert=True)
        return
    
    if call.data == "admin_no_action":
        bot.answer_callback_query(call.id)
        return
    
    not_subscribed = check_subscription(user_id)
    
    if not_subscribed:
        channels_names = "\n".join([f"• {ch['name']}" for ch in not_subscribed])
        bot.answer_callback_query(call.id, "يجب الاشتراك في جميع القنوات أولاً", show_alert=True)
        bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text=f"⚠️ *يجب الاشتراك في جميع القنوات أولاً*\n\n"
                 f"لم تشترك بعد في:\n{channels_names}\n\n"
                 f"اشترك في القنوات ثم اضغط على زر التحقق 👇",
            reply_markup=get_subscription_markup(),
            parse_mode="Markdown"
        )
        return
    
    if call.data == "back_main":
        bot.edit_message_text(
            f"🥶❤️‍🔥 مرحباً يا {user_name} إسِـتٌـمًتٌـعٌ ❤️‍🔥🥶",
            chat_id, message_id,
            reply_markup=get_main_menu(user_id),
            parse_mode="Markdown"
        )
    
    elif call.data == "menu_etisalat":
        show_etisalat_menu(chat_id, message_id)
    elif call.data == "menu_vodafone":
        show_vodafone_menu(chat_id, message_id)
    elif call.data == "menu_orange":
        show_orange_menu(chat_id, message_id)
    elif call.data == "menu_we":
        show_we_menu(chat_id, message_id)
    elif call.data == "menu_other":
        show_other_menu(chat_id, message_id)
    
    elif call.data.startswith("ets_"):
        service_type = call.data.replace("ets_", "")
        if chat_id in user_data:
            del user_data[chat_id]
        user_data[chat_id] = {'service': service_type, 'network': 'etisalat'}
        msg = bot.send_message(chat_id, "📧 من فضلك أدخل الإيميل الخاص بك:")
        bot.register_next_step_handler(msg, process_etisalat_email)
    
    elif call.data == "vod_flex":
        show_flex_bundles(chat_id, message_id)
    elif call.data.startswith("bundle_"):
        bundle_id = call.data.replace("bundle_", "")
        bundle_info = None
        for bundle in FLEX_BUNDLES:
            if bundle['id'] == bundle_id:
                bundle_info = bundle
                break
        if bundle_info:
            if chat_id in user_data:
                del user_data[chat_id]
            user_data[chat_id] = {'action': 'flex', 'bundle_id': bundle_id, 'bundle_info': bundle_info, 'network': 'vodafone'}
            show_confirm_vodafone(chat_id, message_id, 'flex')
    elif call.data == "vod_rollover":
        if chat_id in user_data:
            del user_data[chat_id]
        user_data[chat_id] = {'action': 'rollover', 'network': 'vodafone'}
        show_confirm_vodafone(chat_id, message_id, 'rollover')
    elif call.data == "vod_daily_500":
        if chat_id in user_data:
            del user_data[chat_id]
        user_data[chat_id] = {'action': 'daily_500', 'network': 'vodafone'}
        request_phone_vodafone(chat_id, message_id, 'daily_500')
    elif call.data == "confirm_flex":
        request_phone_vodafone(chat_id, message_id, 'flex')
    elif call.data == "confirm_rollover":
        request_phone_vodafone(chat_id, message_id, 'rollover')
    
    elif call.data == "org_fawazeer":
        if chat_id in user_data:
            del user_data[chat_id]
        user_data[chat_id] = {'action': 'fawazeer', 'network': 'orange'}
        msg = bot.send_message(chat_id, "📱 أدخل رقم الهاتف:")
        bot.register_next_step_handler(msg, process_orange_number)
    elif call.data == "org_promo500":
        if chat_id in user_data:
            del user_data[chat_id]
        user_data[chat_id] = {'action': 'promo_500', 'network': 'orange'}
        msg = bot.send_message(chat_id, "📱 أدخل رقم الهاتف:")
        bot.register_next_step_handler(msg, process_orange_number)
    elif call.data == "org_forgot":
        if chat_id in user_data:
            del user_data[chat_id]
        user_data[chat_id] = {'action': 'forgot_pass', 'network': 'orange'}
        msg = bot.send_message(chat_id, "📱 أدخل رقم الهاتف لاسترجاع كلمة السر:")
        bot.register_next_step_handler(msg, process_orange_number)
    
    elif call.data == "we_info":
        if chat_id in user_data:
            del user_data[chat_id]
        user_data[chat_id] = {'action': 'line_info', 'network': 'we'}
        msg = bot.send_message(chat_id, "📱 أدخل رقم WE الخاص بك:")
        bot.register_next_step_handler(msg, process_we_number)
    elif call.data == "we_usage":
        if chat_id in user_data:
            del user_data[chat_id]
        user_data[chat_id] = {'action': 'usage', 'network': 'we'}
        msg = bot.send_message(chat_id, "📱 أدخل رقم WE لمعرفة الاستهلاك:")
        bot.register_next_step_handler(msg, process_we_number)
    
    elif call.data == "ssh_start":
        start_ssh_process(call)
    elif call.data.startswith('continent_'):
        choose_continent_ssh(call)
    elif call.data.startswith('country_'):
        choose_country_ssh(call)
    elif call.data.startswith('server_'):
        choose_server_ssh(call)
    
    elif call.data == "tempmail_menu":
        show_temp_mail_menu(chat_id, message_id)
    elif call.data == "tempmail_create":
        process_temp_mail_create(chat_id, message_id)
    elif call.data == "tempmail_check":
        process_temp_mail_check(chat_id, message_id)
    elif call.data == "tempmail_new":
        process_temp_mail_create(chat_id, message_id)
    
    elif call.data == "cancel":
        cancel_operation(call)

def handle_subscription_check(call):
    chat_id = call.message.chat.id
    message_id = call.message.message_id
    user_id = call.from_user.id
    
    user_name = get_user_display_name(call.from_user)
    
    not_subscribed = check_subscription(user_id)
    
    if not_subscribed:
        channels_names = "\n".join([f"• {ch['name']}" for ch in not_subscribed])
        bot.answer_callback_query(call.id, "❌ لم تشترك بعد في جميع القنوات", show_alert=True)
        bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text=f"⚠️ *يجب الاشتراك في جميع القنوات أولاً*\n\n"
                 f"لم تشترك بعد في:\n{channels_names}\n\n"
                 f"اشترك في القنوات ثم اضغط على زر التحقق 👇",
            reply_markup=get_subscription_markup(),
            parse_mode="Markdown"
        )
    else:
        bot.answer_callback_query(call.id, "✅ تم التحقق من الاشتراك بنجاح!", show_alert=True)
        bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text=f"🥶❤️‍🔥 مرحباً يا {user_name} إسِـتٌـمًتٌـعٌ ❤️‍🔥🥶",
            reply_markup=get_main_menu(user_id),
            parse_mode="Markdown"
        )

def cancel_operation(call):
    chat_id = call.message.chat.id
    user_id = call.from_user.id
    
    if chat_id in user_data:
        del user_data[chat_id]
    if chat_id in ssh_user_data:
        ssh_user_data.pop(chat_id, None)
    if chat_id in progress_bars:
        progress_bars[chat_id] = False
    
    try:
        bot.delete_state(user_id, chat_id)
    except:
        pass
    
    user_name = get_user_display_name(call.from_user)
    
    bot.edit_message_text(
        chat_id=chat_id,
        message_id=call.message.message_id,
        text=f"❌ تم إلغاء العملية\n\nاختر الشبكة المطلوبة:",
        reply_markup=get_main_menu(call.from_user.id),
        parse_mode="Markdown"
    )

bot.add_custom_filter(custom_filters.StateFilter(bot))

if __name__ == "__main__":
    bot.infinity_polling()