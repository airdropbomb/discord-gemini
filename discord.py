import json
import time
import os
import requests
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

# .env ထဲမှာ OPENROUTER_API_KEY လို့ နာမည်ပြောင်းပေးပါ
discord_token = os.getenv('DISCORD_TOKEN')
openrouter_api_key = os.getenv('OPENROUTER_API_KEY')

last_message_id = None
bot_user_id = None
last_ai_response = None

def log_message(message):
    print(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - {message}")

def generate_reply(prompt, language="id"):
    """Generate a reply using OpenRouter API"""
    global last_ai_response

    # Prompt setting
    if language == "en":
        ai_prompt = f"{prompt}\n\nRespond with only one sentence in casual urban English, like a natural conversation, and do not use symbols."
    else:
        ai_prompt = f"{prompt}\n\nGive 1 sentence in Jakarta slang like a casual chat and don’t use any symbols."

    # OpenRouter Config
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {openrouter_api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/shareithub", # Optional
        "X-Title": "Discord Bot" # Optional
    }
    
    data = {
        "model": "google/gemini-3-flash-preview", # သင်သုံးချင်တဲ့ model name
        "messages": [
            {"role": "user", "content": ai_prompt}
        ]
    }

    for attempt in range(3):
        try:
            response = requests.post(url, headers=headers, json=data)
            response.raise_for_status()
            result = response.json()

            # OpenRouter ရဲ့ response structure က OpenAI နဲ့ တူပါတယ်
            response_text = result['choices'][0]['message']['content'].strip()

            if response_text == last_ai_response:
                log_message("⚠️ AI gave the same reply, trying again...")
                continue
            
            last_ai_response = response_text
            return response_text

        except requests.exceptions.RequestException as e:
            log_message(f"⚠️ Request failed: {e}")
            return None

    return last_ai_response or 'Sorry, cannot reply to the message.'

def send_message(channel_id, message_text, reply_to=None, reply_mode=True):
    headers = {
        'Authorization': f'{discord_token}',
        'Content-Type': 'application/json'
    }
    payload = {'content': message_text}
    if reply_mode and reply_to:
        payload['message_reference'] = {'message_id': reply_to}

    try:
        response = requests.post(f"https://discord.com/api/v9/channels/{channel_id}/messages", json=payload, headers=headers)
        if response.status_code == 201:
            log_message(f"✅ Sent message: {message_text}")
    except Exception as e:
        log_message(f"⚠️ Error sending: {e}")

def auto_reply(channel_id, read_delay, reply_delay, language, reply_mode):
    global last_message_id, bot_user_id
    headers = {'Authorization': f'{discord_token}'}

    # Get Bot ID
    try:
        me = requests.get('https://discord.com/api/v9/users/@me', headers=headers).json()
        bot_user_id = me.get('id')
    except:
        return

    while True:
        try:
            res = requests.get(f'https://discord.com/api/v9/channels/{channel_id}/messages', headers=headers)
            if res.status_code == 200:
                messages = res.json()
                if messages:
                    msg = messages[0]
                    msg_id = msg.get('id')
                    author_id = msg.get('author', {}).get('id')

                    if (last_message_id is None or int(msg_id) > int(last_message_id)) and author_id != bot_user_id:
                        user_text = msg.get('content', '')
                        log_message(f"💬 Received: {user_text}")

                        reply_text = generate_reply(user_text, language)
                        
                        time.sleep(reply_delay)
                        send_message(channel_id, reply_text, reply_to=msg_id if reply_mode else None, reply_mode=reply_mode)
                        last_message_id = msg_id

            time.sleep(read_delay)
        except Exception as e:
            log_message(f"⚠️ Loop error: {e}")
            time.sleep(read_delay)

if __name__ == "__main__":
    channel_id = input("Enter channel ID: ")
    lang = input("Choose language (id/en): ").lower()
    read_delay = int(input("Read delay (sec): "))
    reply_delay = int(input("Reply delay (sec): "))
    
    log_message(f"🚀 Bot started using OpenRouter (Gemini 3 Flash)...")
    auto_reply(channel_id, read_delay, reply_delay, lang, True)
