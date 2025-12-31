import threading
import queue
import time

from fastapi import FastAPI, Request, HTTPException
import uvicorn

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import ElementClickInterceptedException
from selenium.webdriver.common.action_chains import ActionChains
from selenium import webdriver

# -----------------------
# CONFIG (edit these)
# -----------------------
import os
from dotenv import load_dotenv

load_dotenv()

# -----------------------
# CONFIG (edit these)
# -----------------------
WEBTRADER_URL = os.getenv("WEBTRADER_URL")
LOGIN = os.getenv("LOGIN")
PASSWORD = os.getenv("PASSWORD")
SECRET_TOKEN = os.getenv("SECRET_TOKEN")

DEFAULT_VOLUME = "0.25"   # optional: fixed lot size
SYMBOL = "XAUUSD"         # optional: fixed symbol

POST_SETUP_SLEEP_SECONDS = 15  # you asked for 30s after login+symbol selection


# -----------------------
# Shared queue: webhooks -> selenium
# -----------------------
trade_queue: queue.Queue[dict] = queue.Queue()
app = FastAPI()


@app.post("/webhook")
async def webhook(request: Request):
    data = await request.json()

    token = data.get("token")
    if token != SECRET_TOKEN:
        raise HTTPException(status_code=401, detail="bad token")

    # TradingView {{strategy.order.action}} typically sends "buy"/"sell"
    side_raw = (data.get("side") or "").strip().upper()
    if side_raw in ("BUY", "LONG"):
        side = "BUY"
    elif side_raw in ("SELL", "SHORT"):
        side = "SELL"
    else:
        raise HTTPException(status_code=400, detail=f"invalid side: {data.get('side')}")

    trade_queue.put({"side": side, "ts": time.time()})
    return {"ok": True, "queued": side}


# -----------------------
# Selenium helpers
# -----------------------
def js_click(driver, el):
    driver.execute_script("arguments[0].click();", el)


def login_and_select_symbol(driver, wait):
    driver.get(WEBTRADER_URL)

    # Switch into iframe
    iframe = wait.until(EC.presence_of_element_located((By.TAG_NAME, "iframe")))
    driver.switch_to.frame(iframe)

    # Login
    login_input = wait.until(EC.presence_of_element_located((By.NAME, "login")))
    login_input.click()
    login_input.send_keys(LOGIN)

    password_input = wait.until(EC.presence_of_element_located((By.NAME, "password")))
    password_input.click()
    password_input.send_keys(PASSWORD)

    submit_btn = wait.until(
        EC.element_to_be_clickable((By.XPATH, '//button[normalize-space()="Connect to account"]'))
    )
    submit_btn.click()

    time.sleep(1)

    # Switch to SYMBOL once (your existing flow)
    search = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, 'input[placeholder="Search symbol"]')))
    search.click()
    search.send_keys("\u0001")  # Ctrl+A
    search.send_keys("\u0008")  # Backspace
    search.send_keys(SYMBOL)

    time.sleep(1)

    add_btn = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, 'button[title="Add Symbol"]')))
    add_btn.click()

    close_search_btn = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "button.close")))
    close_search_btn.click()

    time.sleep(0.5)

    sym_row = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, f'tr[title="{SYMBOL}"]')))
    sym_row.click()


def close_previous_trade(driver, wait):
    """
    Closes the 'previous trade' by closing the first row in the trades table,
    using the same idea you had in your script:
    - locate trades tbody (div.tbody)
    - find first div.tr[data-id]
    - click button.close inside it (JS click to avoid intercept issues)
    """
    try:
        tbody = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "div.tbody")))

        # first trade row
        first_row = tbody.find_element(By.CSS_SELECTOR, "div.tr[data-id]")

        # close button inside row
        close_btn = first_row.find_element(By.CSS_SELECTOR, "button.close")

        driver.execute_script("arguments[0].scrollIntoView({block:'center'});", close_btn)
        js_click(driver, close_btn)

        # If the UI shows an OK confirmation after close, click it if present.
        # We keep this tolerant: if it doesn't appear, we move on.
        try:
            ok = WebDriverWait(driver, 3).until(
                EC.element_to_be_clickable((By.XPATH, "//button[normalize-space()='OK']"))
            )
            ok.click()
        except Exception:
            pass

        return True

    except Exception:
        # No open trade / table not present / nothing to close
        return False


def place_market_order(driver, wait, side: str):
    # New Order
    new_order = wait.until(
        EC.element_to_be_clickable((
            By.XPATH,
            "//div[contains(@class,'icon-button')][.//span[normalize-space()='New Order']]"
        ))
    )
    new_order.click()

    # Volume
    volume_input = wait.until(
        EC.element_to_be_clickable((
            By.XPATH,
            "//div[contains(@class,'volume')][.//span[normalize-space()='Volume']]//input[@inputmode='decimal']"
        ))
    )
    volume_input.click()
    volume_input.send_keys("\u0001")
    volume_input.send_keys("\u0008")
    volume_input.send_keys(DEFAULT_VOLUME)

    # Buy/Sell by Market
    if side == "BUY":
        trade_btn = wait.until(
            EC.element_to_be_clickable((By.XPATH, "//button[normalize-space()='Buy by Market']"))
        )
    else:
        trade_btn = wait.until(
            EC.element_to_be_clickable((By.XPATH, "//button[normalize-space()='Sell by Market']"))
        )
    trade_btn.click()

    # OK confirm
    ok_button = wait.until(
        EC.element_to_be_clickable((By.XPATH, "//button[normalize-space()='OK']"))
    )
    ok_button.click()


# -----------------------
# Selenium worker
# -----------------------
def selenium_worker():
    driver = webdriver.Chrome()
    wait = WebDriverWait(driver, 20)

    # 1) Login once + select XAUUSD once
    login_and_select_symbol(driver, wait)

    print(f"✅ Logged in and selected {SYMBOL}. Sleeping {POST_SETUP_SLEEP_SECONDS}s...")
    time.sleep(POST_SETUP_SLEEP_SECONDS)

    print("✅ Ready. Waiting for TradingView webhook signals...")

    last_trade_time = 0.0
    cooldown_seconds = 2.0

    while True:
        trade = trade_queue.get()  # blocks until webhook arrives
        side = trade["side"]

        now = time.time()
        if now - last_trade_time < cooldown_seconds:
            print(f"⚠️ Ignored {side} (cooldown)")
            continue
        last_trade_time = now

        print(f"📩 Signal: {side} — closing previous trade (if any) then placing new one...")

        try:
            closed = close_previous_trade(driver, wait)
            if closed:
                print("✅ Previous trade close clicked.")
                time.sleep(0.5)

            place_market_order(driver, wait, side)
            print(f"✅ Executed {side} {SYMBOL} vol={DEFAULT_VOLUME}")

        except Exception as e:
            print("❌ Trade execution failed:", repr(e))


# -----------------------
# Start server + selenium
# -----------------------
if __name__ == "__main__":
    t = threading.Thread(target=selenium_worker, daemon=True)
    t.start()

    uvicorn.run(app, host="127.0.0.1", port=8000)