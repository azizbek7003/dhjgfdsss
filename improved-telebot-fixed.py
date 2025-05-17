import telebot
from telebot import types
import logging
from datetime import datetime
import os
import time
import threading
from telebot.apihelper import ApiException

# Bot tokeni
TOKEN = "7472312675:AAGSHM1HfMoLJwxcFhdAtoSAUJL9OmK3j0A"

# Admin username (ID o'rniga)
ADMIN_USERNAME = "@admin_username"  # O'zingizning Telegram username'ingizni qo'ying

# Asosiy kanallar
CHANNELS = {
    "kanal1": "@kanal1_username",
    "kanal2": "@kanal2_username",
    "kanal3": "@kanal3_username"
}

# Ish turi kanallari - har bir ish turi o'z kanaliga ega
JOB_TYPE_CHANNELS = {
    "Akfa": "@akfa_kanal",
    "Santexnika": "@santexnika_kanal",
    "Elektrik": "@elektrik_kanal",
    "Mebel": "@mebel_kanal",
    "Maishiy texnika": "@texnika_kanal",
    "Qurilish": "@qurilish_kanal",
    "IT": "@it_kanal",
    "Marketing": "@marketing_kanal",
    "Farrosh": "@farrosh_kanal",
    "Bog'bon": "@bogbon_kanal",
    "Haydovchi": "@haydovchi_kanal",
    "Oshpaz": "@oshpaz_kanal"
}

# Ijtimoiy tarmoq havolalari
SOCIAL_LINKS = {
    "telegram": "https://t.me/your_username",
    "instagram": "https://instagram.com/your_username"
}

# Maxfiy kalit so'z
SECRET_KEY = "admin123"

# Viloyatlar ro'yxati (2 qatorga bo'lingan)
REGIONS = [
    ["Toshkent", "Andijon", "Buxoro", "Farg'ona", "Jizzax", "Namangan"],
    ["Navoiy", "Qashqadaryo", "Samarqand", "Sirdaryo", "Surxondaryo", "Xorazm"]
]

# Ish turlari (2 qatorga bo'lingan - har bir qatorda 6 tadan)
JOB_TYPES = [
    ["Akfa", "Santexnika", "Elektrik", "Mebel", "Maishiy texnika", "Qurilish"],
    ["IT", "Marketing", "Farrosh", "Bog'bon", "Haydovchi", "Oshpaz"]
]

# E'lon joylash bo'yicha cheklov
user_posts = {}  # {user_id: last_post_date}

# Foydalanuvchilar holati
user_state = {}  # {user_id: 'state_name'}

# Foydalanuvchi ma'lumotlari
user_data = {}  # {user_id: {'phone': '', 'job_type': '', ...}}

# Thread-safe lock for concurrent access
state_lock = threading.Lock()
data_lock = threading.Lock()
posts_lock = threading.Lock()

# Logging sozlamalari
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Bot yaratish
bot = telebot.TeleBot(TOKEN)

# State konstantalari
CHECK_SUB = 'check_sub'
MAIN_MENU = 'main_menu'
PHONE_NUMBER = 'phone_number'
SELECT_JOB_TYPE = 'select_job_type'
UPLOAD_PHOTO = 'upload_photo'
ASK_MORE_PHOTOS = 'ask_more_photos'
ENTER_PRICE = 'enter_price'
ENTER_DESC = 'enter_desc'
SELECT_REGION = 'select_region'
CONFIRMATION = 'confirmation'
ADMIN_APPROVAL = 'admin_approval'
ADMIN_SET_CHANNEL = 'admin_set_channel'
ADMIN_CHANNEL_NAME = 'admin_channel_name'

def get_channel_buttons():
    """Kanal tugmalarini yaratish"""
    markup = types.InlineKeyboardMarkup(row_width=1)
    for channel_key, channel_name in CHANNELS.items():
        markup.add(types.InlineKeyboardButton(f"➡️ {channel_name} ga a'zo bo'lish", url=f"https://t.me/{channel_name[1:]}"))
    markup.add(types.InlineKeyboardButton("✅ A'zolikni tekshirish", callback_data="check_subscription"))
    return markup

def check_user_subscription(user_id):
    """Foydalanuvchining kanallarga a'zoligini tekshirish"""
    for channel_username in CHANNELS.values():
        try:
            # Telegram API cheklovlari tufayli biroz kutish
            time.sleep(0.1)
            chat_member = bot.get_chat_member(channel_username, user_id)
            status = chat_member.status
            if status == 'left' or status == 'kicked' or status == 'banned':
                return False
        except ApiException as e:
            logger.error(f"API xatoligi: {e}")
            if "429" in str(e):  # Too many requests
                time.sleep(1)  # Telegram API cheklovlarini chetlab o'tish uchun kutish
                try:
                    chat_member = bot.get_chat_member(channel_username, user_id)
                    status = chat_member.status
                    if status == 'left' or status == 'kicked' or status == 'banned':
                        return False
                except Exception as e2:
                    logger.error(f"Ikkinchi urinishda xatolik: {e2}")
                    return False
            else:
                return False
        except Exception as e:
            logger.error(f"Kanal a'zoligini tekshirishda xatolik: {e}")
            return False
    return True

def init_user_data(user_id):
    """Foydalanuvchi ma'lumotlari strukturasini yaratish"""
    with data_lock:
        if user_id not in user_data:
            user_data[user_id] = {
                'photos': [],
                'post_type': '',
                'job_type': '',
                'price': 0,
                'description': '',
                'region': '',
                'phone': ''
            }
        else:
            user_data[user_id]['photos'] = []
            user_data[user_id]['post_type'] = ''
            user_data[user_id]['job_type'] = ''
            user_data[user_id]['price'] = 0
            user_data[user_id]['description'] = ''
            user_data[user_id]['region'] = ''
            user_data[user_id]['phone'] = ''

def set_user_state(user_id, state):
    """Thread-safe foydalanuvchi holatini o'zgartirish"""
    with state_lock:
        user_state[user_id] = state

def get_user_state(user_id):
    """Thread-safe foydalanuvchi holatini olish"""
    with state_lock:
        return user_state.get(user_id)

def format_job_channels_list():
    """Ish kanallarini formatlash - ikki qator matn shaklida"""
    result = "📋 <b>ISH TURI BO'YICHA KANALLAR</b> 📋\n\n"
    
    # Birinchi qatorni tuzish (birinchi 6 ta)
    first_row = list(JOB_TYPE_CHANNELS.items())[:6]
    for job_type, channel in first_row:
        result += f"• <b>{job_type}</b>: {channel}\n"
    
    result += "\n"  # Qatorlar orasiga bo'sh qator
    
    # Ikkinchi qatorni tuzish (qolgan 6 ta)
    second_row = list(JOB_TYPE_CHANNELS.items())[6:]
    for job_type, channel in second_row:
        result += f"• <b>{job_type}</b>: {channel}\n"
    
    return result

# Start buyrug'i
@bot.message_handler(commands=['start'])
def start_command(message):
    user_id = message.from_user.id
    
    # Kun ichida e'lon jo'natganligini tekshirish
    with posts_lock:
        if user_id in user_posts:
            last_post_date = user_posts[user_id]
            today = datetime.now().date()
            if last_post_date == today:
                bot.send_message(user_id, "Siz bugun allaqachon e'lon joylagansiz. Har kuni faqat bitta e'lon joylash mumkin.")
                return
    
    # Yangi sessiya uchun foydalanuvchi ma'lumotlarini tayyorlash
    init_user_data(user_id)
    
    # Kanal a'zolik tugmalarini ko'rsatish
    markup = get_channel_buttons()
    
    bot.send_message(
        user_id,
        f"Assalomu alaykum! Botdan foydalanish uchun quyidagi kanallarga a'zo bo'ling:",
        reply_markup=markup,
        parse_mode='HTML'
    )
    
    # Foydalanuvchi holatini saqlash
    set_user_state(user_id, CHECK_SUB)

# A'zolik tekshiruvi uchun callback
@bot.callback_query_handler(func=lambda call: call.data == "check_subscription")
def check_subscription_callback(call):
    user_id = call.from_user.id
    
    # A'zolikni tekshirish
    is_subscribed = check_user_subscription(user_id)
    
    if is_subscribed:
        bot.edit_message_text(
            "✅ Barcha kanallarga a'zo bo'ldingiz! Endi botdan foydalanishingiz mumkin.", 
            user_id, 
            call.message.message_id
        )
        
        # Asosiy menyu
        show_main_menu(user_id)
    else:
        # Qaysi kanallarga a'zo bo'lmaganligi haqida xabar
        not_subscribed = []
        for channel_key, channel_name in CHANNELS.items():
            try:
                chat_member = bot.get_chat_member(channel_name, user_id)
                if chat_member.status == 'left' or chat_member.status == 'kicked' or chat_member.status == 'banned':
                    not_subscribed.append(channel_name)
            except Exception:
                not_subscribed.append(channel_name)
        
        channels_text = ", ".join(not_subscribed)
        
        bot.edit_message_text(
            f"❌ Siz quyidagi kanal(lar)ga a'zo bo'lmagansiz: {channels_text}\nIltimos, avval a'zo bo'ling.",
            user_id,
            call.message.message_id,
            reply_markup=get_channel_buttons()
        )
        set_user_state(user_id, CHECK_SUB)

def show_main_menu(user_id):
    """Asosiy menyuni ko'rsatish"""
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
    markup.add(types.KeyboardButton("👨‍💼 Ish qidiryapman"))
    markup.add(types.KeyboardButton("🔍 Ishchi kerak"))
    markup.add(types.KeyboardButton("📋 Ish turi bo'yicha kanallar ro'yxati"))
    
    bot.send_message(user_id, "🏠 <b>Asosiy menyu:</b>", reply_markup=markup, parse_mode='HTML')
    set_user_state(user_id, MAIN_MENU)

# Asosiy menyu uchun handler
@bot.message_handler(func=lambda message: get_user_state(message.from_user.id) == MAIN_MENU)
def main_menu_handler(message):
    user_id = message.from_user.id
    text = message.text
    
    if text == "👨‍💼 Ish qidiryapman" or text == "🔍 Ishchi kerak":
        with data_lock:
            # Qaysi tugma bosilganini saqlash
            user_data[user_id]['post_type'] = "Ish qidiryapman" if text.startswith("👨‍💼") else "Ishchi kerak"
        
        # Raqamni ulashish so'rovi
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add(types.KeyboardButton("📱 Raqamni ulashish", request_contact=True))
        markup.add(types.KeyboardButton("🔙 Orqaga"))
        
        bot.send_message(user_id, "📞 Iltimos, telefon raqamingizni ulashing:", reply_markup=markup)
        set_user_state(user_id, PHONE_NUMBER)
    
    elif text == "📋 Ish turi bo'yicha kanallar ro'yxati":
        channels_text = format_job_channels_list()
        bot.send_message(user_id, channels_text, parse_mode='HTML')
    
    elif text == SECRET_KEY:
        # Admin rejimiga o'tish
        markup = types.InlineKeyboardMarkup(row_width=1)
        markup.add(
            types.InlineKeyboardButton("Birinchi kanalni o'zgartirish", callback_data="change_channel_1"),
            types.InlineKeyboardButton("Ikkinchi kanalni o'zgartirish", callback_data="change_channel_2"),
            types.InlineKeyboardButton("Uchinchi kanalni o'zgartirish", callback_data="change_channel_3")
        )
        bot.send_message(user_id, "👑 <b>Admin rejimi.</b> Kanallarni o'zgartirish:", reply_markup=markup, parse_mode='HTML')

# Admin kanal o'zgartirish callback
@bot.callback_query_handler(func=lambda call: call.data.startswith("change_channel_"))
def change_channel_callback(call):
    user_id = call.from_user.id
    channel_num = call.data.split("_")[2]
    
    bot.edit_message_text(
        f"Kanal {channel_num} uchun yangi username kiriting (@username formatida):",
        user_id,
        call.message.message_id
    )
    
    set_user_state(user_id, ADMIN_SET_CHANNEL)
    with data_lock:
        user_data[user_id]['channel_to_change'] = f"kanal{channel_num}"

# Admin kanal o'zgartirish
@bot.message_handler(func=lambda message: get_user_state(message.from_user.id) == ADMIN_SET_CHANNEL)
def admin_set_channel(message):
    user_id = message.from_user.id
    new_channel = message.text
    
    if not new_channel.startswith("@"):
        bot.send_message(user_id, "Kanal nomi @ bilan boshlanishi kerak. Iltimos, qayta kiriting:")
        return
    
    with data_lock:
        channel_key = user_data[user_id]['channel_to_change']
        CHANNELS[channel_key] = new_channel
    
    bot.send_message(user_id, f"✅ {channel_key} muvaffaqiyatli o'zgartirildi: {new_channel}")
    show_main_menu(user_id)

# Telefon raqamni qayta ishlash
@bot.message_handler(func=lambda message: get_user_state(message.from_user.id) == PHONE_NUMBER, content_types=['contact', 'text'])
def process_phone_number(message):
    user_id = message.from_user.id
    
    if message.text == "🔙 Orqaga":
        show_main_menu(user_id)
        return
    
    if message.content_type == 'contact':
        with data_lock:
            user_data[user_id]['phone'] = message.contact.phone_number
    else:
        with data_lock:
            user_data[user_id]['phone'] = message.text
    
    # Ish turini tanlash - inline keyboard
    markup = types.InlineKeyboardMarkup(row_width=3)
    
    # Birinchi qator
    row1_buttons = []
    for job in JOB_TYPES[0]:
        row1_buttons.append(types.InlineKeyboardButton(job, callback_data=f"job_{job}"))
    markup.add(*row1_buttons)
    
    # Ikkinchi qator
    row2_buttons = []
    for job in JOB_TYPES[1]:
        row2_buttons.append(types.InlineKeyboardButton(job, callback_data=f"job_{job}"))
    markup.add(*row2_buttons)
    
    bot.send_message(user_id, "🔨 Ish turini tanlang:", reply_markup=markup)
    set_user_state(user_id, SELECT_JOB_TYPE)

# Ish turi tanlovi (inline keyboard callback)
@bot.callback_query_handler(func=lambda call: call.data.startswith("job_"))
def job_type_callback(call):
    user_id = call.from_user.id
    job_type = call.data.split("_")[1]
    
    with data_lock:
        user_data[user_id]['job_type'] = job_type
    
    # Xabarni yangilash
    bot.edit_message_text(
        f"Siz <b>{job_type}</b> ish turini tanladingiz. Endi rasmlarni yuklang (maksimum 4 ta).",
        user_id,
        call.message.message_id,
        parse_mode='HTML'
    )
    
    set_user_state(user_id, UPLOAD_PHOTO)

# Rasmni yuklash
@bot.message_handler(func=lambda message: get_user_state(message.from_user.id) == UPLOAD_PHOTO, content_types=['photo', 'text'])
def upload_photo_handler(message):
    user_id = message.from_user.id
    
    if message.text == "🔙 Orqaga":
        # Raqamni ulashish so'rovi
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add(types.KeyboardButton("📱 Raqamni ulashish", request_contact=True))
        markup.add(types.KeyboardButton("🔙 Orqaga"))
        
        bot.send_message(user_id, "📞 Iltimos, telefon raqamingizni ulashing:", reply_markup=markup)
        set_user_state(user_id, PHONE_NUMBER)
        return
    
    if message.content_type == 'text':
        bot.send_message(user_id, "📷 Iltimos, rasm yuboring.")
        return
    
    if message.photo:
        photo_id = message.photo[-1].file_id
        
        with data_lock:
            user_data[user_id]['photos'].append(photo_id)
            photo_count = len(user_data[user_id]['photos'])
        
        # Agar 4 ta rasm yuklangan bo'lsa
        if photo_count >= 4:
            # Klaviaturani o'chirish
            markup = types.ReplyKeyboardRemove()
            bot.send_message(user_id, "💰 Narxni kiriting (faqat son, so'mda):", reply_markup=markup)
            set_user_state(user_id, ENTER_PRICE)
            return
        
        # Yana rasm so'rash
        markup = types.InlineKeyboardMarkup()
        markup.row(
            types.InlineKeyboardButton("Ha ✅", callback_data="more_photo"),
            types.InlineKeyboardButton("Yo'q ❌", callback_data="no_more_photo")
        )
        
        bot.send_message(
            user_id, 
            f"📷 {photo_count}-rasm yuklandi. Yana rasm yuklaysizmi?", 
            reply_markup=markup
        )
        set_user_state(user_id, ASK_MORE_PHOTOS)

# Yana rasm so'rash callback
@bot.callback_query_handler(func=lambda call: call.data in ["more_photo", "no_more_photo"] and get_user_state(call.from_user.id) == ASK_MORE_PHOTOS)
def ask_more_photos_callback(call):
    user_id = call.from_user.id
    
    if call.data == "more_photo":
        bot.edit_message_text("📷 Yana rasm yuklang:", user_id, call.message.message_id)
        set_user_state(user_id, UPLOAD_PHOTO)
    else:
        bot.edit_message_text("💰 Narxni kiriting (faqat son, so'mda):", user_id, call.message.message_id)
        set_user_state(user_id, ENTER_PRICE)

# Narxni kiritish
@bot.message_handler(func=lambda message: get_user_state(message.from_user.id) == ENTER_PRICE)
def enter_price_handler(message):
    user_id = message.from_user.id
    
    if message.text == "🔙 Orqaga":
        bot.send_message(user_id, "📷 Rasmlarni yuklang (maksimum 4 ta)")
        set_user_state(user_id, UPLOAD_PHOTO)
        return
    
    try:
        price = int(message.text)
        with data_lock:
            user_data[user_id]['price'] = price
        bot.send_message(user_id, "📝 Maxsulot/xizmat haqida ma'lumot kiriting:")
        set_user_state(user_id, ENTER_DESC)
    except ValueError:
        bot.send_message(user_id, "❌ Iltimos, faqat son kiriting.")

# Tavsif kiritish
@bot.message_handler(func=lambda message: get_user_state(message.from_user.id) == ENTER_DESC)
def enter_description_handler(message):
    user_id = message.from_user.id
    
    if message.text == "🔙 Orqaga":
        bot.send_message(user_id, "💰 Narxni kiriting (faqat son, so'mda):")
        set_user_state(user_id, ENTER_PRICE)
        return
    
    description = message.text
    
    with data_lock:
        user_data[user_id]['description'] = description
    
    # Viloyat tanlash - inline keyboard
    markup = types.InlineKeyboardMarkup(row_width=3)
    
    # Birinchi qator
    row1_buttons = []
    for region in REGIONS[0]:
        row1_buttons.append(types.InlineKeyboardButton(region, callback_data=f"region_{region}"))
    markup.add(*row1_buttons)
    
    # Ikkinchi qator
    row2_buttons = []
    for region in REGIONS[1]:
        row2_buttons.append(types.InlineKeyboardButton(region, callback_data=f"region_{region}"))
    markup.add(*row2_buttons)
    
    bot.send_message(user_id, "📍 Qaysi viloyatdansiz?", reply_markup=markup)
    set_user_state(user_id, SELECT_REGION)

# Viloyat tanlash (inline keyboard callback)
@bot.callback_query_handler(func=lambda call: call.data.startswith("region_"))
def region_callback(call):
    user_id = call.from_user.id
    region = call.data.split("_")[1]
    
    with data_lock:
        user_data[user_id]['region'] = region
    
    # Ma'lumotlarni ko'rsatish va tasdiqlash
    with data_lock:
        job_info = (
            f"<b>Post turi:</b> {user_data[user_id]['post_type']}\n"
            f"<b>Ish turi:</b> {user_data[user_id]['job_type']}\n"
            f"<b>Narx:</b> {user_data[user_id]['price']} so'm\n"
            f"<b>Tavsif:</b> {user_data[user_id]['description']}\n"
            f"<b>Viloyat:</b> {user_data[user_id]['region']}\n"
            f"<b>Telefon:</b> {user_data[user_id]['phone']}"
        )
    
    markup = types.InlineKeyboardMarkup()
    markup.row(
        types.InlineKeyboardButton("✅ Tasdiqlash", callback_data="confirm"),
        types.InlineKeyboardButton("❌ Bekor qilish", callback_data="cancel")
    )
    
    bot.edit_message_text(
        f"<b>Ma'lumotlaringizni tekshiring:</b>\n\n{job_info}", 
        user_id, 
        call.message.message_id,
        parse_mode='HTML',
        reply_markup=markup
    )
    set_user_state(user_id, CONFIRMATION)

# Foydalanuvchi tomonidan tasdiqlash callback
@bot.callback_query_handler(func=lambda call: call.data in ["confirm", "cancel"] and get_user_state(call.from_user.id) == CONFIRMATION)
def confirmation_callback(call):
    user_id = call.from_user.id
    
    if call.data == "confirm":
        # E'lonni adminga yuborish
        with data_lock:
            job_info = (
                f"<b>Yangi e'lon tasdiqlash uchun:</b>\n\n"
                f"<b>Post turi:</b> {user_data[user_id]['post_type']}\n"
                f"<b>Ish turi:</b> {user_data[user_id]['job_type']}\n"
                f"<b>Narx:</b> {user_data[user_id]['price']} so'm\n"
                f"<b>Tavsif:</b> {user_data[user_id]['description']}\n"
                f"<b>Viloyat:</b> {user_data[user_id]['region']}\n"
                f"<b>Telefon:</b> {user_data[user_id]['phone']}\n"
                f"<b>Foydalanuvchi ID:</b> {user_id}"
            )
        
        # Admin tasdiqlash tugmalari
        markup = types.InlineKeyboardMarkup()
        markup.row(
            types.InlineKeyboardButton("✅ Tasdiqlash", callback_data=f"admin_approve_{user_id}"),
            types.InlineKeyboardButton("❌ Rad etish", callback_data=f"admin_reject_{user_id}")
        )
        markup.add(types.InlineKeyboardButton("✏️ Tahrirlash", callback_data=f"admin_edit_{user_id}"))
        
        try:
            # Avval rasmlarni jo'natish
            with data_lock:
                photos = user_data[user_id]['photos']
            
            # To'plam xabar yuborish uchun (katta fayllarni yuborish vaqtida Telegram API cheklovlarini hisobga olish)
            for photo_id in photos:
                try:
                    bot.send_photo(ADMIN_USERNAME, photo_id)
                    time.sleep(0.5)  # Telegram API cheklovlari uchun
                except ApiException as e:
                    if "429" in str(e):  # Too many requests
                        time.sleep(2)  # Longer wait time
                        bot.send_photo(ADMIN_USERNAME, photo_id)
                    else:
                        raise e
            
            # Keyin ma'lumotlarni jo'natish
            bot.send_message(ADMIN_USERNAME, job_info, reply_markup=markup, parse_mode='HTML')
            
            bot.edit_message_text(
                "✅ E'loningiz adminga yuborildi. Tasdiqlashni kuting.", 
                user_id, 
                call.message.message_id
            )
            
            # Kunlik limitni belgilash
            with posts_lock:
                user_posts[user_id] = datetime.now().date()
            
        except Exception as e:
            logger.error(f"Adminga yuborishda xatolik: {e}")
            bot.edit_message_text(
                "❌ Xatolik yuz berdi. Iltimos, qayta urinib ko'ring.", 
                user_id, 
                call.message.message_id
            )
        
        # Foydalanuvchini asosiy menyuga qaytarish
        show_main_menu(user_id)
        
    else:
        bot.edit_message_text("❌ E'lon bekor qilindi.", user_id, call.message.message_id)
        show_main_menu(user_id)

# Admin tasdiqlashi callback
@bot.callback_query_handler(func=lambda call: call.data.startswith("admin_"))
def admin_approval_callback(call):
    parts = call.data.split("_")
    action = parts[1]
    user_id =