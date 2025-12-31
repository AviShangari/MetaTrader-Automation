from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import ElementClickInterceptedException
from selenium.webdriver.common.action_chains import ActionChains
from selenium import webdriver
import time

# Create a Chrome browser instance
driver = webdriver.Chrome()

# Go to the MetaTrader Web page (replace with your broker's WebTrader URL)
driver.get("https://mt5demo2.ftmo.com")

wait = WebDriverWait(driver, 20)

iframe = wait.until(
    EC.presence_of_element_located((By.TAG_NAME, "iframe"))
)

driver.switch_to.frame(iframe)

# Log into the account
login_input = wait.until(EC.presence_of_element_located((By.NAME, "login")))
login_input.click()
login_input.send_keys("1520989378")

password_input = wait.until(EC.presence_of_element_located((By.NAME, "password")))
password_input.click()
password_input.send_keys("?4Z?9@1@Sze")

submit_btn = wait.until(EC.element_to_be_clickable((By.XPATH, '//button[normalize-space()="Connect to account"]')))
submit_btn.click()

time.sleep(1)

search = wait.until(
    EC.element_to_be_clickable((By.CSS_SELECTOR, 'input[placeholder="Search symbol"]'))
)
search.click()

# Replace anything already there
search.send_keys("\u0001")  # Ctrl+A
search.send_keys("\u0008")  # Backspace
search.send_keys("XAUUSD")

time.sleep(0.5)

add_btn = wait.until(
    EC.element_to_be_clickable((By.CSS_SELECTOR, 'button[title="Add Symbol"]'))
)
add_btn.click()

close_btn = wait.until(
    EC.element_to_be_clickable((By.CSS_SELECTOR, "button.close"))
)
close_btn.click()

xau_row = wait.until(
    EC.element_to_be_clickable((
        By.CSS_SELECTOR,
        'tr[title="XAUUSD"]'
    ))
)
xau_row.click()

time.sleep(0.5)

new_order = wait.until(
    EC.element_to_be_clickable((
        By.XPATH,
        "//div[contains(@class,'icon-button')][.//span[normalize-space()='New Order']]"
    ))
)
new_order.click()

volume_input = wait.until(
    EC.element_to_be_clickable((
        By.XPATH,
        "//div[contains(@class,'volume')]"
        "[.//span[normalize-space()='Volume']]"
        "//input[@inputmode='decimal']"
    ))
)

volume_input.click()
volume_input.send_keys("\u0001")  # Ctrl+A
volume_input.send_keys("\u0008")  # Backspace
volume_input.send_keys("0.05")

buy_button = wait.until(
    EC.element_to_be_clickable((
        By.XPATH,
        "//button[normalize-space()='Buy by Market']"
    ))
)
buy_button.click()

ok_button = wait.until(
    EC.element_to_be_clickable((
        By.XPATH,
        "//button[normalize-space()='OK']"
    ))
)
ok_button.click()


tbody = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "div.tbody")))

# Get the first row element (it has data-id)
first_row = tbody.find_element(By.CSS_SELECTOR, "div.tr[data-id]")

# Click the first cell in that row (td)
first_cell = first_row.find_element(By.CSS_SELECTOR, "div.td")

# Debug: confirm Selenium sees size
print("row size:", first_row.size, "cell size:", first_cell.size, "cell text:", first_cell.text)

driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", first_cell)

ActionChains(driver).move_to_element(first_cell).click().perform()

tbody = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "div.tbody")))
first_row = tbody.find_element(By.CSS_SELECTOR, "div.tr[data-id]")
close_btn = first_row.find_element(By.CSS_SELECTOR, "button.close")

driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", close_btn)
driver.execute_script("arguments[0].click();", close_btn)  # JS click is most reliable here

tbody = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "div.tbody")))
first_row = tbody.find_element(By.CSS_SELECTOR, "div.tr[data-id]")
close_btn = first_row.find_element(By.CSS_SELECTOR, "button.close")

driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", close_btn)
driver.execute_script("arguments[0].click();", close_btn)  # JS click is most reliable here

input("Press Enter when you're ready to close the browser...")
driver.quit()