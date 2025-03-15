import requests
from bs4 import BeautifulSoup
from datetime import datetime
import pytz
import asyncio
from telegram import Bot

# Telegram 机器人 TOKEN 和 群聊 Chat ID
TELEGRAM_BOT_TOKEN = "7799347711:AAEQDRavpSXKSNiaPMLBrVvSobnmwuMCL_Q"  # 这里替换为你的 BotFather 生成的 Token
# TELEGRAM_CHAT_ID = "6150321676"  # 我的id
TELEGRAM_CHAT_ID = "-1002680860753" # 群id

bot = Bot(token=TELEGRAM_BOT_TOKEN)

def get_current_date_in_rome():
    rome_tz = pytz.timezone('Europe/Rome')
    current_date = datetime.now(rome_tz).strftime('%d %B %Y')  # 格式化为 "18 Marzo 2025"
    current_date = '13 Marzo 2025' # 后门
    print(f"Current date in Rome timezone: {current_date}")
    return current_date

def scrape_news(url):
    response = requests.get(url)
    if response.status_code != 200:
        print(f"Failed to retrieve the page. Status code: {response.status_code}")
        return []
    
    soup = BeautifulSoup(response.text, 'html.parser')
    news_blocks = soup.find_all('div', class_='post')
    news_list = []
    
    current_date = get_current_date_in_rome()
    
    for news in news_blocks:
        try:
            title_tag = news.find('div', class_='post-headline').find('a')
            title = title_tag.text.strip()
            link = title_tag['href']
            
            date_tag = news.find('div', class_='post-footer')
            date = date_tag.text.split('|')[0].strip() if date_tag else "N/A"
            is_latest = date == current_date
            
            content_tag = news.find('div', class_='post-bodycopy')
            content = content_tag.get_text(" ", strip=True) if content_tag else "No content available"
            
            categories = [cat.text for cat in news.find('div', class_='post-footer').find_all('a')]
            
            news_list.append({
                'title': title,
                'link': link,
                'date': date,
                'is_latest': is_latest,
                'content': content,
                'categories': categories
            })
            
            # 如果是最新新闻，发送到 Telegram 群聊
            if is_latest:
                asyncio.run(send_telegram_message(f"{title}\n {link}"))
        except AttributeError:
            print("Skipping an invalid news block")
    
    return news_list

async def send_telegram_message(message):
    try:
        await bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
        print("Sent to Telegram Group: ", message)
    except Exception as e:
        print("Failed to send message to Telegram Group:", e)

# Example usage
url = "https://www.beniculturali.unipd.it/www/cdl/"  # 请替换为实际的网址
news_data = scrape_news(url)
for news in news_data:
    print(news)

