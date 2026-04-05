import os
import time
import json
import requests
import pyupbit
from dotenv import load_dotenv
from openai import OpenAI
import base64
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains

load_dotenv()

# ============================================================
# 실제 매매 실행 여부 (True: 실제 주문 실행 / False: 시뮬레이션만)
TRADING_ENABLED = False
# ============================================================

def get_fear_and_greed_index():
    """공포 탐욕 지수 최근 7일 데이터 가져오기 (source: alternative.me)"""
    url = "https://api.alternative.me/fng/?limit=7"
    response = requests.get(url, timeout=10)
    response.raise_for_status()
    data = response.json()
    result = []
    for item in data["data"]:
        result.append({
            "value": item["value"],
            "value_classification": item["value_classification"],
            "timestamp": item["timestamp"]
        })
    return result


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

def capture_upbit_chart(screenshot_path="upbit_chart.png"):
    print("#### [System] Start capturing Upbit chart (1h, Bollinger Bands)... ####")
    options = Options()
    options.add_argument("--headless=new") # 모니터 화면 없이 백그라운드 캡쳐
    options.add_argument("--start-maximized")
    driver = webdriver.Chrome(options=options)

    try:
        driver.get("https://upbit.com/full_chart?code=CRIX.UPBIT.KRW-BTC")
        time.sleep(5)  # 차트 초기 로딩 대기

        actions = ActionChains(driver)

        # 1. 주기 메뉴 열기
        menu_btn = WebDriverWait(driver, 15).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "cq-menu.ciq-period"))
        )
        actions.move_to_element(menu_btn).click().perform()
        time.sleep(1)

        # 2. "1시간" 항목 클릭
        items = WebDriverWait(driver, 10).until(
            EC.presence_of_all_elements_located(
                (By.CSS_SELECTOR, "cq-menu.ciq-period cq-menu-dropdown cq-item")
            )
        )
        for item in items:
            txt = driver.execute_script("return arguments[0].innerText;", item).strip()
            if txt == "1시간":
                actions.move_to_element(item).click().perform()
                break
        time.sleep(2)

        driver.fullscreen_window()
        time.sleep(1)

        # 3. 지표 메뉴 열기
        study_menu = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "cq-menu.ciq-studies"))
        )
        actions.move_to_element(study_menu).click().perform()
        time.sleep(1)

        # 4. 볼린저 밴드 클릭
        study_items = WebDriverWait(driver, 10).until(
            EC.presence_of_all_elements_located(
                (By.CSS_SELECTOR, "cq-menu.ciq-studies cq-item")
            )
        )
        for item in study_items:
            txt = driver.execute_script("return arguments[0].innerText;", item).strip()
            if txt == "볼린저 밴드":
                driver.execute_script("arguments[0].scrollIntoView(true);", item)
                time.sleep(0.5)
                actions.move_to_element(item).click().perform()
                break

        time.sleep(1)
        driver.find_element(By.TAG_NAME, "body").click() # 메뉴 닫기
        time.sleep(3)  # 차트 렌더링 대기

        driver.save_screenshot(screenshot_path)
        print(f"#### [System] Chart captured: {screenshot_path} ####")
        return True
    except Exception as e:
        print(f"#### [Error] Failed to capture chart: {e} ####")
        return False
    finally:
        driver.quit()

def encode_image(image_path):
    """이미지 파일을 Base64로 인코딩합니다."""
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')


def execute_trade():
    # 1. 현재 투자 상태 가져오기
    access_key = os.getenv("UPBIT_ACCESS_KEY")
    secret_key = os.getenv("UPBIT_SECRET_KEY")
    upbit = pyupbit.Upbit(access_key, secret_key)

    krw_balance = upbit.get_balance("KRW") or 0.0        # 보유 원화 (None이면 0)
    btc_balance = upbit.get_balance("KRW-BTC") or 0.0   # 보유 BTC (None이면 0)
    current_price = pyupbit.get_current_price("KRW-BTC") or 0.0  # 현재가 (None이면 0)
    btc_value = btc_balance * current_price

    investment_status = {
        "krw_balance": krw_balance,
        "btc_balance": btc_balance,
        "btc_current_price": current_price,
        "btc_value_in_krw": btc_value,
        "total_asset_krw": krw_balance + btc_value
    }
    print(f"\n#### Investment Status ####")
    print(f"  KRW       : {krw_balance:,.0f} KRW")
    print(f"  BTC       : {btc_balance:.8f} BTC")
    print(f"  BTC Price : {current_price:,.0f} KRW")
    print(f"  BTC Value : {btc_value:,.0f} KRW")
    print(f"  Total     : {krw_balance + btc_value:,.0f} KRW")

    # 2. 오더북(호가) 데이터 가져오기
    orderbook = pyupbit.get_orderbook(ticker="KRW-BTC")
    # pyupbit 버전에 따라 리스트 또는 딕셔너리로 반환될 수 있음
    ob = orderbook[0] if isinstance(orderbook, list) else orderbook
    orderbook_data = {
        "total_ask_size": ob.get("total_ask_size", 0),
        "total_bid_size": ob.get("total_bid_size", 0),
        "orderbook_units": ob.get("orderbook_units", [])[:5]  # 상위 5호가만 사용
    }

    # 3. 차트 데이터 가져오기
    # 30일 일봉 OHLCV
    df_daily = pyupbit.get_ohlcv("KRW-BTC", count=30, interval="day")
    # 24시간 시간봉 OHLCV (최근 24개)
    df_hourly = pyupbit.get_ohlcv("KRW-BTC", count=24, interval="minute60")

    # 4. 공포 탐욕 지수 가져오기 (source: alternative.me)
    fng_data = get_fear_and_greed_index()
    print(f"\n#### Fear & Greed Index (Latest): {fng_data[0]['value']} ({fng_data[0]['value_classification']}) ####")

    # 5. 비트코인 최신 뉴스 가져오기 (source: SerpApi Google News)
    news_data = get_bitcoin_news()
    if news_data:
        print(f"#### Latest News ({len(news_data)} articles fetched) ####")
        for i, news in enumerate(news_data[:3], 1):
            # Windows 터미널(CP949) 출력 시 유니코드 에러 방지를 위해 인코딩/디코딩 처리
            safe_title = news['title'].encode('cp949', errors='ignore').decode('cp949')
            print(f"  {i}. [{news['date']}] {safe_title}")

    # === [통합] 차트 캡쳐 (Selenium, Bollinger Bands) ===
    chart_img_path = "upbit_chart.png"
    chart_captured = capture_upbit_chart(chart_img_path)

    # 6. AI에게 데이터 제공하고 판단 받기
    client = OpenAI()

    news_section = ""
    if news_data:
        news_section = (
            f"## Latest Bitcoin News Headlines (source: Google News via SerpApi):\n"
            f"{json.dumps(news_data, ensure_ascii=False, indent=2)}\n\n"
            "Use the news sentiment to identify potential market-moving events "
            "(e.g., regulation, ETF approval, exchange hacks, macro events).\n\n"
        )

    user_content = (
        f"## Current Investment Status:\n{json.dumps(investment_status, ensure_ascii=False)}\n\n"
        f"## Orderbook (Top 5 ask/bid):\n{json.dumps(orderbook_data, ensure_ascii=False)}\n\n"
        f"## Bitcoin 30-Day Daily Chart (OHLCV):\n{df_daily.to_json()}\n\n"
        f"## Bitcoin 24-Hour Hourly Chart (OHLCV):\n{df_hourly.to_json()}\n\n"
        f"## Fear and Greed Index (Recent 7 days, source: alternative.me):\n"
        f"{json.dumps(fng_data, ensure_ascii=False)}\n\n"
        "The Fear and Greed Index ranges from 0 (Extreme Fear) to 100 (Extreme Greed).\n"
        "- 0~24: Extreme Fear\n"
        "- 25~44: Fear\n"
        "- 45~55: Neutral\n"
        "- 56~74: Greed\n"
        "- 75~100: Extreme Greed\n\n"
        f"{news_section}"
        "Please use all the data above to make your decision."
    )

    # 멀티모달(텍스트+이미지) 형태로 메시지 객체 구성
    user_message_content = [
        {"type": "text", "text": user_content}
    ]

    # 차트가 정상적으로 캡쳐되었다면 Base64로 첨부
    if chart_captured:
        base64_image = encode_image(chart_img_path)
        user_message_content.append({
            "type": "image_url",
            "image_url": {
                "url": f"data:image/png;base64,{base64_image}"
            }
        })
    else:
        print("#### [Warning] Chart image could not be attached ####")

    system_prompt = (
        "You are a Bitcoin investment expert. "
        "Based on the investment status, orderbook, chart data, Fear and Greed Index, latest news, "
        "and the attached chart image (which contains 1-hour candles and Bollinger Bands), "
        "please tell me whether I should buy, sell, or hold.\n"
        "Consider all signals together:\n"
        "- Investment status: current KRW/BTC holdings and total asset value\n"
        "- Orderbook: ask/bid ratio indicates short-term supply/demand pressure\n"
        "- Daily chart (30d): overall trend, support/resistance levels\n"
        "- Hourly chart (24h): short-term momentum and recent price action\n"
        "- Visual Chart: Analyze the attached screenshot of the Upbit chart directly. Identify the relationship between the recent 1-hour candles and the Bollinger Bands (e.g., upper/lower band touches, squeeze, breakout) to support your technical reasoning.\n"
        "- Sentiment: extreme fear can be a buying opportunity, extreme greed can signal a sell\n"
        "- News: positive news (ETF, adoption) may signal buy; negative news (hack, ban) may signal sell\n"
        "Response in json format.\n\n"
        "Response Example:\n"
        "{\"decision\":\"buy\", \"reason\": \"some technical reason including visual chart analysis\"}\n"
        "{\"decision\":\"sell\", \"reason\": \"some technical reason including visual chart analysis\"}\n"
        "{\"decision\":\"hold\", \"reason\": \"some technical reason including visual chart analysis\"}"
    )

    response = client.chat.completions.create(
        model="gpt-4o",  # Vision 지원이 견고하고 가격/성능 밸런스가 좋은 gpt-4o 사용 추천
        messages=[
            {
                "role": "system",
                "content": system_prompt
            },
            {
                "role": "user",
                "content": user_message_content
            }
        ],
        response_format={"type": "json_object"}
    )

    result = json.loads(response.choices[0].message.content)

    print(f"\n#### AI Decision: {result['decision'].upper()} ####")
    print(f"#### Reason: {result['reason']} ####")

    # 7. 판단 결과에 따라 매수, 매도, 홀드 자동매매 진행
    if not TRADING_ENABLED:
        print("#### [Simulation Mode] Actual trading disabled (TRADING_ENABLED = False) ####")
        return

    if result["decision"] == "buy":
        my_balance = upbit.get_balance("KRW") or 0.0
        if my_balance < 5000:  # 최소 주문 금액 확인
            print("### Buy Order Failed: Insufficient Balance ###")
        else:
            # 시장가 매수 (보유한 원화 전부로 매수)
            order = upbit.buy_market_order("KRW-BTC", my_balance * 0.9995)
            print("#### Buy Order Executed ####")
            print(f"#### Order: {order} ####")

    elif result["decision"] == "sell":
        my_balance = upbit.get_balance("KRW-BTC") or 0.0
        current_price = pyupbit.get_current_price("KRW-BTC") or 0.0
        if (my_balance * current_price) < 5000:  # 최소 주문 금액 확인
            print("### Sell Order Failed: Insufficient Balance ###")
        else:
            # 시장가 매도 (보유한 BTC 전부 매도)
            order = upbit.sell_market_order("KRW-BTC", my_balance)
            print("#### Sell Order Executed ####")
            print(f"#### Order: {order} ####")

    else:  # hold
        print("#### Hold ####")


# 반복 실행 (예: 1시간마다)
if __name__ == "__main__":
    execute_trade()
    # while True:
    #     execute_trade()
    #     time.sleep(3600)  # 3600초 = 1시간
