import requests
from bs4 import BeautifulSoup
from datetime import datetime
import json
import time
import schedule

def load_config():
    try:
        with open('config.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        default_config = {
            "url": "https://www.meinspeiseplan.info/rbzw",
            "days_to_show": ["Montag", "Donnerstag"],
            "gotify": {
                "server_url": "https://your-gotify-server.com",
                "api_key": "YOUR-API-KEY-HERE",
                "enabled": True
            },
            "check_time": "06:00"
        }
        with open('config.json', 'w', encoding='utf-8') as f:
            json.dump(default_config, f, indent=4)
        return default_config

def get_weekday_german(date_obj):
    weekdays = {
        0: "Montag",
        1: "Dienstag",
        2: "Mittwoch",
        3: "Donnerstag",
        4: "Freitag",
        5: "Samstag",
        6: "Sonntag"
    }
    return weekdays[date_obj.weekday()]

def is_notification_day():
    config = load_config()
    current_weekday = get_weekday_german(datetime.now())
    return current_weekday in config['days_to_show']

def send_gotify_notification(server_url, api_key, title, message):
    try:
        response = requests.post(
            f"{server_url}/message",
            headers={"X-Gotify-Key": api_key},
            json={
                "title": title,
                "message": message,
                "priority": 5
            }
        )
        response.raise_for_status()
        return True
    except Exception as e:
        print(f"Gotify Error: {e}")
        return False

def get_menu(config):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }

    try:
        response = requests.get(config['url'], headers=headers)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')

        date_label = soup.find('div', class_='datelabel')
        if date_label:
            date_text = date_label.get_text(strip=True)
            try:
                date_parts = [part for part in date_text.split() if '.' in part][0]
                date_obj = datetime.strptime(date_parts, '%d.%m.%Y')
                weekday = get_weekday_german(date_obj)
                formatted_date = f"{weekday} {date_obj.strftime('%d.%m.%Y')}"
            except:
                return None, []
        else:
            return None, []

        content = soup.find_all('div', id='maindish')
        menu_items = []
        for item in content:
            text = item.get_text(strip=True)
            if text and not text.startswith('Tagesgericht'):
                menu_items.append(text)

        menu_items = menu_items[:3]
        return formatted_date, menu_items
    except Exception as e:
        print(f"Error: {e}")
        return None, []

def format_menu_message(date, menu_items):
    message = [f"📅 {date}\n"]
    message.append("🍽️ Heute gibt es:\n")

    for i, item in enumerate(menu_items, 1):
        message.append(f"\n{i}. {item}")

    message.append("\n\n- - - - - - - - - -")
    return "\n".join(message)

def check_and_send_menu():
    # First check if today is a notification day
    if not is_notification_day():
        return

    config = load_config()
    date, menu_items = get_menu(config)

    if date and menu_items and config['gotify']['enabled']:
        menu_message = format_menu_message(date, menu_items)
        send_gotify_notification(
            config['gotify']['server_url'],
            config['gotify']['api_key'],
            "🍴 RBZ Speiseplan",
            menu_message
        )

def run_scheduler():
    config = load_config()
    schedule.every().day.at(config['check_time']).do(check_and_send_menu)

    print(f"Speiseplan service started. Checking at {config['check_time']} on {', '.join(config['days_to_show'])}")

    while True:
        schedule.run_pending()
        time.sleep(60)

if __name__ == "__main__":
    run_scheduler()
