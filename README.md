# NoteChain — CSRF + Cookie Tossing CTF Challenge

**Author:** huang  
**Category:** Web Exploitation  
**Difficulty:** Medium  

## Description

NoteChain is a note-sharing web app with XSS and a tricky CSRF protection bypass.

The goal is to chain **Cookie Tossing** (injecting a duplicate `csrf_token` cookie with a narrower path scope) with **CSRF** (Cross-Site Request Forgery) to hijack the admin account and read the flag at `/flag`.

## Setup

### 1. Start with Docker

```bash
docker compose up --build
```

Two services:
- `app` — Flask app on port 5000  
- `bot` — admin bot on port 8888 (`POST /report` with `url=<exploit>`)

### 2. Open the app

```
http://localhost:5000
```

## Vulnerability

### Cookie Tossing

The `/cookie/set` endpoint sets cookies with `Path=/change-password`. When the browser later redirects to `/change-password`, both the original csrf_token cookie (`Path=/`) and the tossed csrf_token cookie (`Path=/change-password`) are sent together, creating duplicate cookies with the same name but different scopes.

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
   - Loads an img from `/cookie/set?name=csrf_token&value=YOUR_TOKEN` to toss your token into the victim's browser with `Path=/change-password`
   - Redirects via JS to `/change-password?password=NEWPASS&csrf_token=YOUR_TOKEN`  
3. Submit the note URL to the admin bot at `/report`  
4. Admin bot visits → cookie tossed → CSRF succeeds → password changed  
5. Log in as `admin` with the new password  
6. Visit `/flag?password=NEWPASS` to read the flag  

### Running the Solver

```bash
# From host (app on localhost:5000, bot on localhost:8888)
pip install requests
python solver.py

# Or from Docker network
docker run --rm \
  --network notechain-ctf_default \
  -v "$(pwd)/solver.py:/solver.py" \
  -e BOT_URL=http://bot:8888 \
  python:3.11-slim \
  sh -c "pip install requests -q && python /solver.py"
```

## No Unintended Solutions

- **Session forgery** — session tokens are random 256-bit values stored in DB. Setting `session=admin` won't work.  
- **Predictable CSRF token** — `csrf_token` is `secrets.token_hex(16)`, not derived from username.  
- **CSRF token via JS** — `csrf_token` cookie is `httponly`, so XSS cannot read it. Cookie Tossing is required to inject a known token.  
- **Direct flag access via XSS** — `/flag` requires the admin's current password as a query parameter. Only the intended chain (change password → login → read flag) works.  
- **IDOR** — the flag is stored as an environment variable, not in a note. Viewing admin's notes only shows a decoy.  

## Flag

```
CTF{cs1rf_c00k1e_t0ss1ng_ftw}
```

## License

MIT
