import os
import pyupbit
from dotenv import load_dotenv

load_dotenv()

# 1. 현재 투자 상태 가져오기
access_key = os.getenv("UPBIT_ACCESS_KEY")
secret_key = os.getenv("UPBIT_SECRET_KEY")

if not access_key or not secret_key:
    print("#### [Error] UPBIT_ACCESS_KEY 또는 UPBIT_SECRET_KEY가 .env에 설정되지 않았습니다. ####")
    exit(1)

upbit = pyupbit.Upbit(access_key, secret_key)

# 2. 전체 잔고 조회 (보유한 모든 자산)
print("\n==============================")
print("   Upbit 계좌 잔고 조회")
print("==============================")

balances = upbit.get_balances()

# 에러 응답 처리 (dict로 반환되면 에러)
if isinstance(balances, dict) and "error" in balances:
    err = balances["error"]
    print(f"#### [Error] API 오류: {err.get('name')} - {err.get('message')} ####")
    exit(1)

if not balances or not isinstance(balances, list):
    print("#### [Error] 잔고 조회 실패 - API 키를 확인하세요. ####")
    exit(1)

for b in balances:
    currency = b.get("currency", "")
    balance = float(b.get("balance", 0))
    locked = float(b.get("locked", 0))
    avg_buy_price = float(b.get("avg_buy_price", 0))

    if currency == "KRW":
        print(f"\n  [원화]")
        print(f"    보유 KRW   : {balance:>20,.0f} 원")
        print(f"    주문 중    : {locked:>20,.0f} 원")
    else:
        ticker = f"KRW-{currency}"
        try:
            current_price = pyupbit.get_current_price(ticker) or 0.0
        except Exception:
            current_price = 0.0  # KRW 마켓 없는 코인은 0으로 처리
        eval_amount = balance * current_price
        profit = ((current_price - avg_buy_price) / avg_buy_price * 100) if avg_buy_price > 0 else 0.0
        print(f"\n  [{currency}]")
        print(f"    보유 수량  : {balance:>20.8f} {currency}")
        print(f"    주문 중    : {locked:>20.8f} {currency}")
        print(f"    평균 매수가: {avg_buy_price:>20,.0f} 원")
        if current_price > 0:
            print(f"    현재가     : {current_price:>20,.0f} 원")
            print(f"    평가 금액  : {eval_amount:>20,.0f} 원")
            print(f"    수익률     : {profit:>19.2f} %")
        else:
            print(f"    현재가     : {'KRW 마켓 없음':>20}")

# 3. 총 자산 요약
print("\n==============================")
krw_balance = upbit.get_balance("KRW") or 0.0
btc_balance = upbit.get_balance("KRW-BTC") or 0.0
current_price = pyupbit.get_current_price("KRW-BTC") or 0.0
btc_value = btc_balance * current_price
total_asset = krw_balance + btc_value

print(f"  KRW        : {krw_balance:>20,.0f} 원")
print(f"  BTC        : {btc_balance:>20.8f} BTC")
print(f"  BTC 현재가  : {current_price:>20,.0f} 원")
print(f"  BTC 평가금액: {btc_value:>20,.0f} 원")
print(f"  ──────────────────────────────")
print(f"  총 자산     : {total_asset:>20,.0f} 원")
print("==============================\n")