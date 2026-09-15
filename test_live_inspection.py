from selenium import webdriver
from selenium.webdriver.edge.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time, os

options = Options()
options.add_argument('--headless=new')
options.add_argument('--window-size=1440,1400')
driver = webdriver.Edge(options=options)
driver.get('http://localhost:8501')

WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.CSS_SELECTOR, 'input[type="file"]')))
file_input = driver.find_element(By.CSS_SELECTOR, 'input[type="file"]')
file_input.send_keys(os.path.abspath('data_SEGO170_stack.xlsx'))
time.sleep(3)

# 1. Inspect stFileUploader outerHTML
uploader = driver.find_element(By.CSS_SELECTOR, '[data-testid="stFileUploader"]')
print("=== FILE UPLOADER HTML ===")
print(uploader.get_attribute('outerHTML'))

# Click Compute button
btn = driver.find_element(By.XPATH, '//button[contains(., "Jalankan Komputasi")]')
driver.execute_script("arguments[0].click();", btn)
time.sleep(5)

# Check for errors on page
errors = driver.find_elements(By.CSS_SELECTOR, '[data-testid="stException"], [data-testid="stAlert"]')
for err in errors:
    print("=== ERROR FOUND ===")
    print(err.text)

# 2. Inspect stTabs outerHTML
tabs = driver.find_elements(By.CSS_SELECTOR, '[data-testid="stTabs"]')
if tabs:
    print("=== TABS HTML ===")
    print(tabs[0].get_attribute('outerHTML')[:2000])

driver.quit()
