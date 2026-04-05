# SerpApi Google News API Test
# https://serpapi.com/google-news-api
# Free Plan
# 250 searches / month

import os
import time
import json
import requests
import pyupbit
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

def get_bitcoin_news():
    """SerpApi Google News API로 비트코인 최신 뉴스 헤드라인 가져오기"""
    serpapi_key = os.getenv("SERPAPI_API_KEY")
    if not serpapi_key:
        print("#### [Warning] SERPAPI_API_KEY not set, skipping news ####")
        return []

    url = "https://serpapi.com/search.json"
    params = {
        "engine": "google_news",
        "q": "Bitcoin BTC crypto",
        "gl": "us",
        "hl": "en",
        "api_key": serpapi_key
    }

    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()

        news_list = []
        for item in data.get("news_results", [])[:10]:  # 최신 10개
            # 단일 뉴스 기사
            if "title" in item and "source" in item:
                news_list.append({
                    "title": item.get("title", ""),
                    "date": item.get("iso_date", item.get("date", ""))
                })
            # stories 묶음에서 첫 번째 기사 추출
            elif "stories" in item:
                for story in item["stories"][:2]:
                    news_list.append({
                        "title": story.get("title", ""),
                        "date": story.get("iso_date", story.get("date", ""))
                    })

        return news_list[:10]  # 최대 10개

    except Exception as e:
        print(f"#### [Warning] Failed to fetch news: {e} ####")
        return []

print(get_bitcoin_news())