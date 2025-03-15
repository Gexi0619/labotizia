import requests
from bs4 import BeautifulSoup
from datetime import datetime
import pytz
import os
import argparse
import json
import asyncio
from telegram import Bot

SENT_NEWS_JSON = "sent_news.json"

# 读取 GitHub Secrets（从环境变量获取）
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

bot = Bot(token=TELEGRAM_BOT_TOKEN)

ITALIAN_MONTHS = {
    'Gennaio': '01', 'Febbraio': '02', 'Marzo': '03', 'Aprile': '04',
    'Maggio': '05', 'Giugno': '06', 'Luglio': '07', 'Agosto': '08',
    'Settembre': '09', 'Ottobre': '10', 'Novembre': '11', 'Dicembre': '12'
}

def get_today_date_rome():
    rome_tz = pytz.timezone('Europe/Rome')
    return datetime.now(rome_tz)

def parse_italian_date(date_str):
    try:
        parts = date_str.split()
        if len(parts) != 3:
            return None
        day, month_it, year = parts
        month = ITALIAN_MONTHS.get(month_it)
        if not month:
            return None
        date_formatted = f"{day.zfill(2)}/{month}/{year}"
        return datetime.strptime(date_formatted, "%d/%m/%Y")
    except Exception:
        return None

def load_sent_news():
    if not os.path.exists(SENT_NEWS_JSON):
        with open(SENT_NEWS_JSON, 'w', encoding='utf-8') as f:
            json.dump([], f)
        return []
    else:
        with open(SENT_NEWS_JSON, 'r', encoding='utf-8') as f:
            return json.load(f)

def print_sent_news(sent_news_list):
    print(f"\n📁 Contenuto di '{SENT_NEWS_JSON}':")
    for item in sent_news_list:
        print(f"🔗 {item['link']} | 📅 {item['date']}")
    print(f"📊 Totale notizie già inviate: {len(sent_news_list)}\n")

def save_sent_news(news_item):
    data = load_sent_news()
    data.insert(0, news_item)
    with open(SENT_NEWS_JSON, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def is_already_sent(news_item, sent_news_list):
    return any(
        item['link'] == news_item['link'] and item['date'] == news_item['date']
        for item in sent_news_list
    )

def scrape_news(url):
    response = requests.get(url)
    if response.status_code != 200:
        print(f"[ERROR] Failed to retrieve the page. Status code: {response.status_code}")
        return []

    soup = BeautifulSoup(response.text, 'html.parser')
    news_blocks = soup.find_all('div', class_='post')
    news_list = []

    for news in news_blocks:
        try:
            title_tag = news.find('div', class_='post-headline').find('a')
            title = title_tag.text.strip()
            link = title_tag['href']

            date_tag = news.find('div', class_='post-footer')
            date_str = date_tag.text.split('|')[0].strip() if date_tag else "N/A"

            news_list.append({
                'title': title,
                'link': link,
                'date_str': date_str
            })
        except AttributeError:
            print("[WARNING] Blocco notizia non valido, salto...")

    return news_list

async def send_telegram_message_batch(messages):
    for title, message in messages:
        print(f"📡 Inviando su Telegram: {title}")
        try:
            await bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
            print(f"✅ Inviato con successo: {title}")
        except Exception as e:
            print(f"❌ Errore nell'invio di: {title}")
            print("   Dettaglio errore:", e)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--mark-all-sent", action="store_true", help="Segna tutte le notizie attuali come già inviate")
    args = parser.parse_args()

    url = "https://www.beniculturali.unipd.it/www/cdl/"
    news_data = scrape_news(url)

    if args.mark_all_sent:
        sent_news_list = load_sent_news()
        count = 0
        for news in news_data:
            item = {'title': news['title'], 'link': news['link'], 'date': news['date_str']}
            if not is_already_sent(item, sent_news_list):
                save_sent_news(item)
                print(f"✔️ Marked as sent: {item['title']}\n   🔗 {item['link']}")
                count += 1
        print(f"\n✅ Totale aggiunto: {count} notizie.")
    else:
        sent_news_list = load_sent_news()
        print_sent_news(sent_news_list)
        today = get_today_date_rome().date()

        messages_to_send = []

        for news in news_data:
            title = news['title']
            link = news['link']
            date_str = news['date_str']
            date_obj = parse_italian_date(date_str)
            if date_obj:
                delta_days = (today - date_obj.date()).days
            else:
                delta_days = "?"

            news_item = {'title': title, 'link': link, 'date': date_str}
            is_sent = is_already_sent(news_item, sent_news_list)

            print(f"\n📰 Titolo: {title}")
            print(f"🔗 Link: {link}")
            print(f"📅 Data pubblicazione: {date_str}")
            print(f"📤 Già inviato? {'✅ Sì' if is_sent else '❌ No'}")
            print(f"📊 Differenza con oggi: {delta_days} giorni")

            if not is_sent:
                message = f"👩🏻‍🔬 {title}\n📅 Pubblicato {delta_days} giorni fa\n🔗 {link}"
                messages_to_send.append((title, message))
                save_sent_news(news_item)

        if messages_to_send:
            asyncio.run(send_telegram_message_batch(messages_to_send))
