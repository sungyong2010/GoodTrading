import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains


# Chrome 옵션 설정
options = Options()
options.add_argument("--start-maximized")

driver = webdriver.Chrome(options=options)

try:
    driver.get("https://upbit.com/full_chart?code=CRIX.UPBIT.KRW-BTC")
    time.sleep(5)  # 차트 초기 로딩 대기

    actions = ActionChains(driver)

    # 1. 주기 메뉴 열기 (CSS Selector 사용 - XPath의 span[2] 구조가 실제 DOM과 다름)
    menu_btn = WebDriverWait(driver, 15).until(
        EC.element_to_be_clickable((By.CSS_SELECTOR, "cq-menu.ciq-period"))
    )
    actions.move_to_element(menu_btn).click().perform()
    time.sleep(1)

    # 2. "1시간" 항목 클릭 - 전체 목록 중 8번째 (0-index 기준 7)
    items = WebDriverWait(driver, 10).until(
        EC.presence_of_all_elements_located(
            (By.CSS_SELECTOR, "cq-menu.ciq-period cq-menu-dropdown cq-item")
        )
    )
    print(f"#### 주기 항목 수: {len(items)} ####")
    
    # 확실히 1시간을 선택하도록 수정
    one_hour_btn = None
    for item in items:
        txt = driver.execute_script("return arguments[0].innerText;", item).strip()
        if txt == "1시간":
            one_hour_btn = item
            break
            
    if one_hour_btn:
        actions.move_to_element(one_hour_btn).click().perform()
        print(f"#### 1시간 봉 선택 완료: [1시간] ####")
    else:
        print("#### [Error] 1시간 항목을 찾지 못했습니다. ####")
    time.sleep(2)

    # 전체 화면 (주기 선택 후에 전환)
    driver.fullscreen_window()
    time.sleep(1)

    # 3. 지표 메뉴 열기 - CSS Selector
    study_menu = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.CSS_SELECTOR, "cq-menu.ciq-studies"))
    )
    actions.move_to_element(study_menu).click().perform()
    print("#### 지표 메뉴 열기 완료 ####")
    time.sleep(2)

    # 4. 볼린저 밴드 항목 클릭 - innerText(JS)로 탐색
    study_items = WebDriverWait(driver, 10).until(
        EC.presence_of_all_elements_located(
            (By.CSS_SELECTOR, "cq-menu.ciq-studies cq-item")
        )
    )
    print(f"#### 지표 항목 수: {len(study_items)} ####")

    bollinger_found = False
    
    # 우선 정확히 '볼린저 밴드' 텍스트를 찾습니다.
    for item in study_items:
        txt = driver.execute_script("return arguments[0].innerText;", item).strip()
        if txt == "볼린저 밴드":
            print(f"#### 볼린저 밴드 항목 텍스트: [{txt}] ####")
            driver.execute_script("arguments[0].scrollIntoView(true);", item)
            time.sleep(0.5)
            actions.move_to_element(item).click().perform()
            bollinger_found = True
            print("#### 볼린저 밴드 추가 완료 ####")
            break

    if not bollinger_found:
        print("#### 볼린저 밴드 항목을 찾지 못했습니다 - 텍스트 목록을 확인하세요 ####")
    time.sleep(1)

    # 5. 메뉴 닫기
    driver.find_element(By.TAG_NAME, "body").click()
    time.sleep(3)  # 차트 완전 렌더링 대기

    # 6. 스크린샷 저장
    screenshot_path = "upbit_chart.png"
    driver.save_screenshot(screenshot_path)
    print(f"#### 차트 캡처 완료: {screenshot_path} ####")

finally:
    driver.quit()



