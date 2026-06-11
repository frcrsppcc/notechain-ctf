# NoteChain — CSRF + Cookie Tossing CTF Challenge

**Author:** huang  
**Category:** Web Exploitation  
**Difficulty:** Medium  

## Description

NoteChain is a note-sharing web app with two subdomains:

- **app.ctf.local** — main app (login, notes, password change)
- **api.ctf.local** — API endpoint that can set cookies for the entire domain

The goal is to chain **Cookie Tossing** (injecting a duplicate `csrf_token` cookie via a broader domain scope) with **CSRF** (Cross-Site Request Forgery) to hijack the admin account and read the flag at `/flag`.

## Setup

### 1. Hosts file

```
127.0.0.1 app.ctf.local api.ctf.local
```

### 2. Start with Docker

```bash
docker compose up --build
```

Three services:
- `app` — Flask app on port 5000  
- `nginx` — reverse proxy on port 80 routing `app.ctf.local` and `api.ctf.local`  
- `bot` — admin bot on port 8888 (`POST /report` with `url=<exploit>`)

### 3. Open the app

```
http://app.ctf.local
http://api.ctf.local/cookie/set?name=test&value=hello
```

## Vulnerability

### Cookie Tossing

The `/cookie/set` endpoint on `api.ctf.local` sets cookies with `Domain=.ctf.local` — valid for all subdomains. This injects a second `csrf_token` cookie alongside the admin's original one.

### CSRF Protection Bypass

`/change-password` checks the double-submit cookie by iterating **all** `csrf_token` cookies:

```python
tokens = request.cookies.getlist("csrf_token")
if csrf not in tokens:
    return "csrf token mismatch"
```

If an attacker injects their own `csrf_token` via cookie tossing, the submitted token matches one of the cookie values, bypassing the check.

### Exploit Chain

1. Register an account → get your random `csrf_token` cookie  
2. Create a note with HTML that:
   - Loads an img from `api.ctf.local/cookie/set?name=csrf_token&value=YOUR_TOKEN` to toss your token into the victim's browser  
   - Redirects via JS to `app.ctf.local/change-password?password=NEWPASS&csrf_token=YOUR_TOKEN`  
3. Submit the note URL to `bot:8888/report`  
4. Admin bot visits → cookie tossed → CSRF succeeds → password changed  
5. Log in as `admin` with the new password  
6. Visit `/flag` to read the flag  

## No Unintended Solutions

- **Session forgery** — session tokens are random 256-bit values stored in DB. Setting `session=admin` won't work.  
- **Predictable CSRF token** — `csrf_token` is `secrets.token_hex(16)`, not derived from username.  
- **IDOR** — the flag is stored as an environment variable, not in a note. Viewing admin's notes only shows a decoy.  

## Flag

```
CTF{cs1rf_c00k1e_t0ss1ng_ftw}
```

## License

MIT
