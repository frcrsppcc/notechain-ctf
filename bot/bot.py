from flask import Flask, request
from playwright.sync_api import sync_playwright
import os, threading

app = Flask(__name__)

APP_URL = os.environ.get("APP_URL", "http://app.ctf.local")

@app.route('/report', methods=['POST'])
def report():
    url = request.form.get('url', '')
    if not url:
        return 'need url parameter'

    def visit():
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True, args=['--no-sandbox'])
            ctx = browser.new_context(
                ignore_https_errors=True,
                user_agent='Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36'
            )
            page = ctx.new_page()

            # login as admin
            page.goto(APP_URL + '/login', wait_until='networkidle')
            page.fill('input[name=username]', 'admin')
            page.fill('input[name=password]', 's3cur3_admin_p4ssw0rd_1337')
            page.click('button[type=submit]')
            page.wait_for_timeout(1000)

            # go to attacker's page
            page.goto(url, wait_until='networkidle')
            page.wait_for_timeout(3000)

            browser.close()

    threading.Thread(target=visit, daemon=True).start()
    return 'admin will visit your url shortly'

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8888)
