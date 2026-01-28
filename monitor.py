from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
import json
import os
from datetime import datetime
import smtplib
from email.mime.text import MIMEText
import re
import time

STATE_FILE = "job_count.json"

def get_job_count():
    url = "https://www.amazon.jobs/content/en/career-programs/university/jobs-for-grads?country%5B%5D=US"
    
    chrome_options = Options()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-gpu')
    
    # For GitHub Actions - use system chromedriver
    service = Service('/usr/bin/chromedriver') if os.path.exists('/usr/bin/chromedriver') else None
    
    try:
        if service:
            driver = webdriver.Chrome(service=service, options=chrome_options)
        else:
            driver = webdriver.Chrome(options=chrome_options)
            
        driver.get(url)
        
        wait = WebDriverWait(driver, 20)
        wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        
        print("⏳ Waiting for page to fully load...")
        time.sleep(5)
        
        for attempt in range(3):
            page_text = driver.page_source
            match = re.search(r'(\d+)\s+OPEN\s+JOBS', page_text, re.IGNORECASE)
            
            if match:
                count = int(match.group(1))
                print(f"✅ Found job count (US only): {count}")
                driver.quit()
                return count
            
            if attempt < 2:
                print(f"🔄 Attempt {attempt + 1} failed, waiting 2 more seconds...")
                time.sleep(2)
        
        print("❌ Could not find job count after 3 attempts")
        driver.quit()
        return None
        
    except Exception as e:
        print(f"❌ Error: {e}")
        try:
            driver.quit()
        except:
            pass
        return None

def load_previous_count():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, 'r') as f:
            data = json.load(f)
            return data.get('count')
    return None

def save_current_count(count):
    with open(STATE_FILE, 'w') as f:
        json.dump({
            'count': count,
            'updated': datetime.now().isoformat()
        }, f)

def send_email(old_count, new_count):
    from_email = os.environ.get('FROM_EMAIL')
    to_email = os.environ.get('TO_EMAIL')
    password = os.environ.get('EMAIL_PASSWORD')
    
    if not all([from_email, to_email, password]):
        print("❌ Email credentials not set!")
        return
    
    msg = MIMEText(f"""
Amazon Jobs for Grads Update (US ONLY)!

Previous: {old_count or 'N/A'} positions
Current: {new_count} positions
Change: {new_count - (old_count or 0):+d}

Check here: https://www.amazon.jobs/content/en/career-programs/university/jobs-for-grads?country%5B%5D=US

Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
""")
    
    msg['Subject'] = f'🚨 Amazon US Jobs Update: {new_count} openings'
    msg['From'] = from_email
    msg['To'] = to_email
    
    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(from_email, password)
            server.send_message(msg)
        print("✅ Email sent!")
    except Exception as e:
        print(f"❌ Email error: {e}")

def main():
    print(f"🔍 Checking US Amazon Jobs for Grads at {datetime.now()}")
    
    current_count = get_job_count()
    
    if current_count is None:
        print("⚠️ Could not get job count")
        return
    
    previous_count = load_previous_count()
    
    save_current_count(current_count)
    
    if previous_count is None:
        print(f"💾 First run - saved count: {current_count}")
    elif previous_count != current_count:
        print(f"🔔 Change detected: {previous_count} → {current_count}")
        send_email(previous_count, current_count)
    else:
        print(f"✅ No change ({current_count} US positions)")

if __name__ == "__main__":
    main()