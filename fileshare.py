import uuid 
import time #Import at the top of your script

def process_file(message):
    try:
        file_entry = None
        if message.document:
            file_entry = {"type": "document", "file_id": message.document.file_id}
        elif message.photo:
            file_entry = {"type": "photo", "file_id": message.photo[-1].file_id}  # Highest resolution
        elif message.video:
            file_entry = {"type": "video", "file_id": message.video.file_id}
        elif message.audio:
            file_entry = {"type": "audio", "file_id": message.audio.file_id}
        else:
            bot.reply_to(message, "❌ Invalid file type. Please send a document, photo, video, or audio.")
            return

        # Generate a unique ID
        unique_id = str(uuid.uuid4())[:8]  # Shorten UUID for readability

        # Store in database
        FILE_COLLECTION.insert_one({"_id": unique_id, "file": file_entry})

        # Generate the link
        bot.reply_to(
            message,
            f"✅ Link generated:\nhttps://t.me/{bot.get_me().username}?start={unique_id}",
            disable_web_page_preview=True
        )
    except Exception as e:
        logging.error(f"Error processing file: {e}")
        bot.reply_to(message, "❌ An error occurred. Please try again.")
        
import telebot
import hashlib 
from telebot.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    ReplyKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardRemove,
)
import json
import logging
from time import time, sleep
from pymongo import MongoClient
from flask import Flask 
from threading import Thread 

# Bot configuration
BOT_TOKEN = "7882079471:AAE-LDbgk6sCgcI6-QxzZR-_CWf8hP03U_U"
PRIVATE_CHANNEL_ID = -1002367696663  # Your private channel ID
ADMIN_ID = 6897739611  # Your admin user ID
CHANNEL_USERNAME = "@join_hyponet"  # Replace with your channel's username

bot = telebot.TeleBot(BOT_TOKEN)

MONGO_URI = "mongodb+srv://fileshare:fileshare@fileshare.ixlhi.mongodb.net/?retryWrites=true&w=majority&appName=fileshare"
DB_NAME = "telegram_bot"
COLLECTION_NAME = "buttons"



client = MongoClient(MONGO_URI)
db = client[DB_NAME]
buttons_collection = db[COLLECTION_NAME]
FILE_COLLECTION = db["file_links"]
BATCH_COLLECTION = db["batch_links"]

app = Flask('')

@app.route('/')
def home():
    return "I am alive"

def run_http_server():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run_http_server)
    t.start()
    
    
# Set up logging to monitor any issues
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

def load_data():
    try:
        data = {}
        for item in buttons_collection.find():
            data[item["_id"]] = {"files": item["files"], "password": item.get("password")}
        return data
    except Exception as e:
        logging.error(f"Error loading data from MongoDB: {e}")
        return {}

def save_data(data):
    try:
        buttons_collection.delete_many({})  # Clear existing data
        for button_name, button_info in data.items():
            buttons_collection.insert_one({"_id": button_name, "files": button_info["files"], "password": button_info.get("password")})
    except Exception as e:
        logging.error(f"Error saving data to MongoDB: {e}")


button_data = load_data()

# Helper function to check if the user is a member of the channel
membership_cache = {}

def is_user_member(user_id):
    current_time = time()
    # Clear the cached status on each check (forces a fresh status check)
    if user_id in membership_cache:
        del membership_cache[user_id]
    try:
        status = bot.get_chat_member(CHANNEL_USERNAME, user_id).status
        logging.info(f"User {user_id} status: {status}")
        is_member = status in ["member", "administrator", "creator"]
        membership_cache[user_id] = (is_member, current_time)
        return is_member
    except telebot.apihelper.ApiTelegramException as e:
        if "USER_NOT_FOUND" in str(e):
            logging.warning(f"User {user_id} not found in channel.")
        else:
            logging.error(f"Error checking membership: {e}")
        return False

@bot.message_handler(commands=["start"])
def start(message):
    try:
        args = message.text.split()
        if len(args) > 1:
            if args[1].startswith("batch_"):  # Check if it's a batch link
                batch_id = args[1].split("_")[1]
                batch_entry = BATCH_COLLECTION.find_one({"_id": batch_id})
                if batch_entry:
                    send_files(message.chat.id, batch_entry["files"])
                    return

            else:
                unique_id = args[1]
                file_entry = FILE_COLLECTION.find_one({"_id": unique_id})
                if file_entry:
                    send_files(message.chat.id, [file_entry["file"]])
                    return

        if is_user_member(message.from_user.id):
            markup = ReplyKeyboardMarkup(resize_keyboard=True)
            for button_name in button_data.keys():
                markup.add(KeyboardButton(button_name))
            
            inline_markup = InlineKeyboardMarkup()
            owner_button = InlineKeyboardButton("Owner🗿", url="https://t.me/botplays90")
            inline_markup.add(owner_button)

            bot.send_message(
                message.chat.id,
                "𝐖𝐞𝐥𝐜𝐨𝐦𝐞 𝐓𝐨 𝐅𝐢𝐥𝐞 𝐒𝐡𝐚𝐫𝐢𝐧𝐠 𝐁𝐨𝐭 𝐁𝐲 @botplays90\n\n𝐔𝐬𝐞 𝐓𝐡𝐞 𝐁𝐞𝐥𝐨𝐰 𝐁𝐮𝐭𝐭𝐨𝐧𝐬 𝐓𝐨 𝐆𝐞𝐭 𝐅𝐢𝐥𝐞𝐬", 
                reply_markup=inline_markup,
            )
        else:
            markup = InlineKeyboardMarkup()
            join_button = InlineKeyboardButton("Join Channel", url=f"https://t.me/{CHANNEL_USERNAME.lstrip('@')}")
            check_button = InlineKeyboardButton("Check Membership", callback_data="check_membership")
            markup.add(join_button, check_button)
            bot.send_message(
                message.chat.id,
                "𝐉𝐨𝐢𝐧 𝐎𝐮𝐫 𝐂𝐡𝐚𝐧𝐧𝐞𝐥 𝐅𝐢𝐫𝐬𝐭 𝐓𝐨 𝐔𝐬𝐞 𝐓𝐡𝐞 𝐁𝐨𝐭",
                reply_markup=markup,
            )
    except Exception as e:
        logging.error(f"Error in start handler: {e}")

# Callback handler for "Check Membership" button
@bot.callback_query_handler(func=lambda call: call.data == "check_membership")
def check_membership(call):
    try:
        if is_user_member(call.from_user.id):
            bot.answer_callback_query(call.id, "𝐉𝐨𝐢𝐧𝐞𝐝 𝐒𝐮𝐜𝐜𝐞𝐬𝐬𝐟𝐮𝐥𝐥𝐲 𝐘𝐨𝐮 𝐂𝐚𝐧 𝐏𝐫𝐨𝐜𝐞𝐞𝐝!✅")
            bot.delete_message(call.message.chat.id, call.message.message_id)
            start(call.message)
        else:
            bot.answer_callback_query(call.id, "𝐘𝐨𝐮 𝐇𝐚𝐯𝐞𝐧'𝐭 𝐉𝐨𝐢𝐧𝐞𝐝 𝐎𝐮𝐫 𝐂𝐡𝐚𝐧𝐧𝐞𝐥 𝐘𝐞𝐭❌!")
    except Exception as e:
        logging.error(f"Error in check_membership callback: {e}")
        bot.answer_callback_query(call.id, "An error occurred. Please try again later.")
        
@bot.message_handler(commands=["remove_button"])
def remove_button(message):
    if message.from_user.id != ADMIN_ID:
        bot.reply_to(message, "𝐘𝐨𝐮 𝐀𝐫𝐞 𝐍𝐨𝐭 𝐀𝐮𝐭𝐡𝐨𝐫𝐢𝐳𝐞𝐝 𝐓𝐨 𝐏𝐞𝐫𝐟𝐨𝐫𝐦 𝐓𝐡𝐢𝐬 𝐀𝐜𝐭𝐢𝐨𝐧.")
        return
    if not button_data:
        bot.reply_to(message, "𝐍𝐨 𝐁𝐮𝐭𝐭𝐨𝐧𝐬 𝐀𝐯𝐚𝐢𝐥𝐚𝐛𝐥𝐞 𝐓𝐨 𝐑𝐞𝐦𝐨𝐯𝐞.")
        return

    markup = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    for button_name in button_data.keys():
        markup.add(KeyboardButton(button_name))

    msg = bot.send_message(
        message.chat.id,
        "𝐒𝐞𝐥𝐞𝐜𝐭 𝐓𝐡𝐞 𝐁𝐮𝐭𝐭𝐨𝐧 𝐘𝐨𝐮 𝐖𝐚𝐧𝐭 𝐓𝐨 𝐑𝐞𝐦𝐨𝐯𝐞:",
        reply_markup=markup,
    )
    bot.register_next_step_handler(msg, confirm_removal)

def confirm_removal(message):
    try:
        button_name = message.text
        if buttons_collection.find_one({"_id": button_name}):
            buttons_collection.delete_one({"_id": button_name})
            bot.send_message(message.chat.id, f"Button '{button_name}' has been successfully removed.", reply_markup=ReplyKeyboardRemove())
        else:
            bot.reply_to(message, "Invalid selection. Please use /remove_button again to select a valid button.")
    except Exception as e:
        logging.error(f"Error removing button: {e}")
        
@bot.message_handler(commands=["genlink"])
def generate_link(message):
    bot.send_message(message.chat.id, "📤 Send the file you want to generate a link for:")
    bot.register_next_step_handler(message, process_file)
    
@bot.message_handler(commands=["batch"])
def start_batch(message):
    unique_id = str(uuid.uuid4())[:8]  # Generate a unique batch ID
    bot.send_message(message.chat.id, "📤 Send all the files one by one you want to group under one link.\n\n✅ Send `/done` when you're finished.")
    bot.register_next_step_handler(message, collect_batch_files, unique_id, [])


def collect_batch_files(message, batch_id, file_list):
    try:
        if message.text == "/done":
            if not file_list:
                bot.reply_to(message, "❌ No files were added. Batch creation canceled.")
                return
            
            # Store the batch in the database
            BATCH_COLLECTION.insert_one({"_id": batch_id, "files": file_list})

            # Generate and send the link
            bot.reply_to(
                message,
                f"✅ Batch link generated:\nhttps://t.me/{bot.get_me().username}?start=batch_{batch_id}",
                disable_web_page_preview=True
            )
            return

        file_entry = None
        if message.document:
            file_entry = {"type": "document", "file_id": message.document.file_id}
        elif message.photo:
            file_entry = {"type": "photo", "file_id": message.photo[-1].file_id}  # Highest resolution
        elif message.video:
            file_entry = {"type": "video", "file_id": message.video.file_id}
        elif message.audio:
            file_entry = {"type": "audio", "file_id": message.audio.file_id}
        else:
            bot.reply_to(message, "❌ Invalid file type. Please send a document, photo, video, or audio.")
            bot.register_next_step_handler(message, collect_batch_files, batch_id, file_list)
            return

        file_list.append(file_entry)  # Add file to the batch list
        bot.reply_to(message, "✅ File added. Send more or type `/done` to finish.")

        # Keep collecting files
        bot.register_next_step_handler(message, collect_batch_files, batch_id, file_list)

    except Exception as e:
        logging.error(f"Error collecting batch files: {e}")
        bot.reply_to(message, "❌ An error occurred. Please try again.")

@bot.message_handler(commands=["update"])
def update_menu_buttons(message):
    try:
        if is_user_member(message.from_user.id):
            # Create a new ReplyKeyboardMarkup for the updated buttons
            if button_data:
                markup = ReplyKeyboardMarkup(resize_keyboard=True)
                for button_name in button_data.keys():
                    markup.add(KeyboardButton(button_name))
                bot.reply_to(
                    message,
                    "𝐌𝐞𝐧𝐮 𝐁𝐮𝐭𝐭𝐨𝐧𝐬 𝐔𝐩𝐝𝐚𝐭𝐞𝐝 𝐒𝐮𝐜𝐜𝐞𝐬𝐬𝐟𝐮𝐥𝐥𝐲! 𝐔𝐬𝐞 𝐓𝐡𝐞 𝐁𝐮𝐭𝐭𝐨𝐧𝐬 𝐁𝐞𝐥𝐨𝐰 𝐓𝐨 𝐀𝐜𝐜𝐞𝐬𝐬 𝐅𝐢𝐥𝐞𝐬.",
                    reply_markup=markup,
                )
            else:
                # No buttons available, remove the keyboard
                bot.reply_to(
                    message,
                    "𝐍𝐨 𝐁𝐮𝐭𝐭𝐨𝐧𝐬 𝐀𝐫𝐞 𝐀𝐯𝐚𝐢𝐥𝐚𝐛𝐥𝐞 𝐀𝐭 𝐓𝐡𝐞 𝐌𝐨𝐦𝐞𝐧𝐭. 𝐏𝐥𝐞𝐚𝐬𝐞 𝐂𝐡𝐞𝐜𝐤 𝐁𝐚𝐜𝐤 𝐋𝐚𝐭𝐞𝐫.",
                    reply_markup=ReplyKeyboardRemove(),
                )
        else:
            # User needs to join the channel first
            bot.reply_to(message, "𝐘𝐨𝐮 𝐍𝐞𝐞𝐝 𝐓𝐨 𝐉𝐨𝐢𝐧 𝐎𝐮𝐫 𝐂𝐡𝐚𝐧𝐧𝐞𝐥 𝐓𝐨 𝐔𝐬𝐞 𝐓𝐡𝐢𝐬 𝐅𝐞𝐚𝐭𝐮𝐫𝐞.")
    except Exception as e:
        logging.error(f"Error in update_menu_buttons: {e}")
        
@bot.message_handler(commands=["help"])
def help_command(message):
    try:
        help_text = (
            "📖 **Help Guide**\n\n"
            "Here are the commands you can use with this bot:\n\n"
            "🔹 **/start** - Start the bot and display the menu buttons.\n"
            "🔹 **/update** - Refresh the menu buttons to ensure they are up-to-date.\n"
            "🔹 **/help** - Display this help message.\n\n"
            "📋 **How to Use the Bot:**\n"
            "1. Join our channel [here](https://t.me/join_hyponet).\n"
            "2. Use the menu buttons to access files associated with each button.\n"
            "3. If a button is password-protected, you will be prompted to enter the password.\n\n"
            
"-------------------------------------------------------------------\n\n"
            "🛠 **Admin Commands (For Admin Only):**\n"
            "🔹 /add_button - Add a new button to the menu (optional password).\n"
            "🔹 /remove_button** - Remove an existing button from the menu.\n\n"
            "💬 If you have any issues or need further assistance, contact [the owner](https://t.me/botplays90).\n\n"
            "Enjoy using the bot! 😊"
        )
        bot.send_message(message.chat.id, help_text, parse_mode="Markdown", disable_web_page_preview=True)
    except Exception as e:
        logging.error(f"Error in help_command: {e}")
        bot.reply_to(message, "An error occurred while displaying the help message. Please try again later.")
        
# Command to add a button (Admin only)
# Command to add a button (Admin only)
@bot.message_handler(commands=["addbutton"])
def add_button(message):
    if message.from_user.id != ADMIN_ID:
        bot.reply_to(message, "𝐘𝐨𝐮 𝐀𝐫𝐞 𝐍𝐨𝐭 𝐀𝐮𝐭𝐡𝐨𝐫𝐢𝐳𝐞𝐝 𝐓𝐨 𝐏𝐞𝐫𝐟𝐨𝐫𝐦 𝐓𝐡𝐢𝐬 𝐀𝐜𝐭𝐢𝐨𝐧.")
        return
    msg = bot.reply_to(message, "𝐒𝐞𝐧𝐝 𝐌𝐞 𝐓𝐡𝐞 𝐍𝐚𝐦𝐞 𝐎𝐟 𝐓𝐡𝐞 𝐍𝐞𝐰 𝐁𝐮𝐭𝐭𝐨𝐧.")
    bot.register_next_step_handler(msg, save_button_name)

def save_button_name(message):
    try:
        button_name = message.text
        if buttons_collection.find_one({"_id": button_name}):
            bot.reply_to(message, "𝐁𝐮𝐭𝐭𝐨𝐧 𝐀𝐥𝐫𝐞𝐚𝐝𝐲 𝐄𝐱𝐢𝐬𝐭𝐬!")
        else:
            msg = bot.reply_to(message, f"𝐁𝐮𝐭𝐭𝐨𝐧 '{button_name}' 𝐀𝐝𝐝𝐞𝐝! 𝐍𝐨𝐰, 𝐃𝐨 𝐘𝐨𝐮 𝐖𝐚𝐧𝐭 𝐓𝐨 𝐒𝐞𝐭 𝐀 𝐏𝐚𝐬𝐬𝐰𝐨𝐫𝐝 𝐅𝐨𝐫 𝐓𝐡𝐢𝐬 𝐁𝐮𝐭𝐭𝐨𝐧? (𝐎𝐩𝐭𝐢𝐨𝐧𝐚𝐥)\n\n"
"𝐒𝐞𝐧𝐝 '𝐲𝐞𝐬' 𝐓𝐨 𝐒𝐞𝐭 𝐀 𝐏𝐚𝐬𝐬𝐰𝐨𝐫𝐝, 𝐎𝐫 '𝐧𝐨' 𝐓𝐨 𝐒𝐤𝐢𝐩.")
            bot.register_next_step_handler(msg, save_button_password, button_name)

            # Send a message to the private channel indicating the button was created
            bot.send_message(
                PRIVATE_CHANNEL_ID,
                f"New button <code>{button_name}</code> added! Send files here and use the button caption as the file caption.",
                parse_mode="HTML"
            )
    except Exception as e:
        logging.error(f"Error saving button name: {e}")


def save_button_password(message, button_name):
    try:
        if message.text.lower() == "yes":
            msg = bot.reply_to(message, f"𝐏𝐥𝐞𝐚𝐬𝐞 𝐒𝐞𝐧𝐝 𝐀 𝐏𝐚𝐬𝐬𝐰𝐨𝐫𝐝 𝐅𝐨𝐫 𝐓𝐡𝐞 '{button_name}' 𝐁𝐮𝐭𝐭𝐨𝐧.")
            bot.register_next_step_handler(msg, hash_and_store_password, button_name)
        else:
            # Save the button without a password
            button_data[button_name] = {"files": [], "password": None}
            save_data(button_data)
            bot.reply_to(message, f"𝐁𝐮𝐭𝐭𝐨𝐧 '{button_name}' 𝐂𝐫𝐞𝐚𝐭𝐞𝐝 𝐖𝐢𝐭𝐡𝐨𝐮𝐭 𝐏𝐚𝐬𝐬𝐰𝐨𝐫𝐝.")
            
            
            
    except Exception as e:
        logging.error(f"Error in save_button_password: {e}")
    
@bot.message_handler(func=lambda message: buttons_collection.find_one({"_id": message.text}))
def handle_button_press(message):
    try:
        if is_user_member(message.from_user.id):
            button_name = message.text
            button = buttons_collection.find_one({"_id": button_name})
            
            if button.get("password"):
                msg = bot.reply_to(message, f"𝐄𝐧𝐭𝐞𝐫 𝐓𝐡𝐞 𝐏𝐚𝐬𝐬𝐊𝐞𝐲 𝐓𝐨 𝐆𝐞𝐭 𝐅𝐢𝐥𝐞𝐬 '{button_name}' button🔐:")
                bot.register_next_step_handler(msg, verify_password, button_name)
            else:
                send_files(message.chat.id, button["files"])
        else:
            bot.reply_to(message, "𝐘𝐨𝐮 𝐧𝐞𝐞𝐝 𝐭𝐨 𝐣𝐨𝐢𝐧 𝐨𝐮𝐫 𝐜𝐡𝐚𝐧𝐧𝐞𝐥 𝐭𝐨 𝐮𝐬𝐞 𝐭𝐡𝐢𝐬 𝐟𝐞𝐚𝐭𝐮𝐫𝐞.")
    except Exception as e:
        logging.error(f"Error handling button press: {e}")

def verify_password(message, button_name):
    try:
        user_password = message.text
        hashed_user_password = hashlib.sha256(user_password.encode()).hexdigest()
        
        button = buttons_collection.find_one({"_id": button_name})
        if button and hashed_user_password == button["password"]:
            bot.reply_to(message, "𝐏𝐚𝐬𝐬𝐊𝐞𝐲 𝐕𝐞𝐫𝐢𝐟𝐢𝐞𝐝 ‼️ 𝐀𝐜𝐜𝐞𝐬𝐬 𝐆𝐫𝐚𝐧𝐭𝐞𝐝.")
            send_files(message.chat.id, button["files"])
        else:
            bot.reply_to(message, "𝐈𝐧𝐜𝐨𝐫𝐫𝐞𝐜𝐭 𝐏𝐚𝐬𝐬𝐊𝐞𝐲 ❌🔐.")
    except Exception as e:
        logging.error(f"Error verifying password: {e}")
        
def send_files(chat_id, files):
    for file in files:
        if file["type"] == "photo":
            bot.send_photo(chat_id, file["file_id"])
        elif file["type"] == "document":
            bot.send_document(chat_id, file["file_id"])
        elif file["type"] == "video":
            bot.send_video(chat_id, file["file_id"])
        elif file["type"] == "audio":
            bot.send_audio(chat_id, file["file_id"])
                    

# Listen for files in the private channel and save them
@bot.channel_post_handler(content_types=["document", "photo", "video", "audio"])
def save_file_from_channel(message):
    try:
        caption = message.caption or ""
        if caption in button_data:
            file_entry = None
            # Check for the type of file being sent and create the corresponding entry
            if message.document:
                file_entry = {"type": "document", "file_id": message.document.file_id}
            elif message.photo:
                file_entry = {"type": "photo", "file_id": message.photo[-1].file_id}  # Highest resolution
            elif message.video:
                file_entry = {"type": "video", "file_id": message.video.file_id}
            elif message.audio:
                file_entry = {"type": "audio", "file_id": message.audio.file_id}
            
            # If a valid file entry was found, save it
            if file_entry:
                button_data[caption]["files"].append(file_entry)
                save_data(button_data)
                bot.send_message(
                    PRIVATE_CHANNEL_ID,
                    f"File saved under button '{caption}'.",
                )
        else:
            bot.send_message(
                PRIVATE_CHANNEL_ID,
                f"Received file but no button found with caption '{caption}'. Please check the caption!",
            )
    except Exception as e:
        logging.error(f"Error saving file from channel: {e}")
        
def hash_and_store_password(message, button_name):
    try:
        password = message.text
        # Hash the password using SHA-256
        hashed_password = hashlib.sha256(password.encode()).hexdigest()
        
        # Save the button with the hashed password
        button_data[button_name] = {"files": [], "password": hashed_password}
        save_data(button_data)
        
        bot.reply_to(message, f"Button '{button_name}' added with a password.")
        
        # Notify the private channel
        bot.send_message(
            PRIVATE_CHANNEL_ID,
            f"New button <code>{button_name}</code> added! Send files here and use the button caption as the file caption.",
            parse_mode="HTML",
        )
    except Exception as e:
        logging.error(f"Error hashing and storing password: {e}")
        
if __name__ == "__main__":
    keep_alive()  # Start the Flask keep-alive server
    
    while True:
        try:
            bot.polling(none_stop=True, timeout=10, interval=0.1)
        except Exception as e:
            logging.error(f"Polling error: {e}")
            sleep(5)
