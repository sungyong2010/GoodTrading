import os
from dotenv import load_dotenv
load_dotenv()


# 3. 판단 결과에 따라 매수, 매도, 홀드 자동매매 진행하기
def execute_trade():
  # 1. upbit chart data 가져오기(30일 일봉)
  # https://github.com/sharebook-kr/pyupbit
  import pyupbit
  df = pyupbit.get_ohlcv("KRW-BTC", count=30, interval="day")

  # 2. AI에게 데이타 제공하고 판단 받기
  from openai import OpenAI
  client = OpenAI()

  response = client.chat.completions.create(
      model="gpt-4.1",
      messages=[
          {
              "role": "system",
              "content": (
                  "You are a Bitcoin investment expert. "
                  "Based on the chart data provided, please tell me whether I should buy, sell, or hold.\n"
                  "Response in json format.\n\n"
                  "Response Example:\n"
                  "{\"decision\":\"buy\", \"reason\": \"some technical reason\"}\n"
                  "{\"decision\":\"sell\", \"reason\": \"some technical reason\"}\n"
                  "{\"decision\":\"hold\", \"reason\": \"some technical reason\"}"
              )
          },
          {
              "role": "user",
              "content": df.to_json()
          }
      ],
      response_format={"type": "json_object"}
  )

  result = response.choices[0].message.content
  import json
  result = json.loads(result)
  # print(type(result))
  # print(result["decision"])
  import pyupbit
  access_key = os.getenv("UPBIT_ACCESS_KEY")
  secret_key = os.getenv("UPBIT_SECRET_KEY")
  upbit = pyupbit.Upbit(access_key, secret_key)

  print(f"\n#### AI Decision: ", {result["decision"].upper()}, "####" )
  print(f"#### Reason: ", {result["reason"]}, "####" )

  if result["decision"] == "buy":
      my_balance = upbit.get_balance("KRW")
      if my_balance < 5000:  # 최소 주문 금액 확인
          print("### Buy Order Failed: Insufficient Balance ###")
      else:
          # 시장가 매수
          print("#### Buy Order Executed ####")
          upbit.buy_market_order("KRW-BTC", my_balance * 0.9995)  #  보유한 원화 전부로 매수
          print("buy:", result["reason"])
  elif result["decision"] == "sell":
      my_balance = upbit.get_balance("KRW-BTC")
      current_price = pyupbit.get_orderbook(ticker="KRW-BTC")["orderbook_units"][0]["ask_price"]
      if (my_balance * current_price) < 5000:  # 최소 주문 금액 확인
          print("### Sell Order Failed: Insufficient Balance ###")
      else:
          # 시장가 매도
          upbit.sell_market_order("KRW-BTC", upbit.get_balance("KRW-BTC"))  #
          print("sell:", result["reason"])
  else:
      print("hold:", result["reason"])

while True:
  import time
  time.sleep(10)
  execute_trade()
