# NoteChain — CSRF + Cookie Tossing CTF Challenge

**Author:** huang  
**Category:** Web Exploitation  
**Difficulty:** Medium  

## Description

NoteChain is a note-sharing web app with two subdomains:

- **app.ctf.local** — main app (login, notes, password change)
- **api.ctf.local** — API endpoint (cookie management)

Players must chain **Cookie Tossing** (injecting a duplicate cookie via a broader domain scope) with **CSRF** (Cross-Site Request Forgery) to hijack the admin account and read the flag.

## Goal

Change the admin's password via CSRF, log in as admin, and visit `/flag`.

## Setup

### 1. Hosts file

Add these lines to your `/etc/hosts` (Linux/Mac) or `C:\Windows\System32\drivers\etc\hosts` (Windows):

```
127.0.0.1 app.ctf.local api.ctf.local
```

### 2. Start with Docker

```bash
docker compose up --build
```

Three services start:
- `app` — Flask app on port 5000 (internal, proxied by nginx)
- `nginx` — reverse proxy on port 80, routing `app.ctf.local` and `api.ctf.local`
- `bot` — admin bot on port 8888 (`POST /report` with `url=<exploit>`)

### 3. Open the app

```
http://app.ctf.local
http://api.ctf.local/cookie/set?name=test&value=hello
```

## Vulnerability

### Cookie Tossing

The `/cookie/set` endpoint on `api.ctf.local` sets cookies with `Domain=.ctf.local` — valid for all subdomains. This can inject a second `csrf_token` cookie with a known value.

### CSRF Protection Bypass

The password change endpoint (`GET /change-password`) uses a double-submit cookie pattern. The check iterates through **all** `csrf_token` cookies and accepts if any match:

```python
tokens = request.cookies.getlist("csrf_token")
if csrf not in tokens:
    return "csrf token mismatch"
```

By injecting a controlled `csrf_token` cookie, the attacker's value is added to the list and the CSRF check passes.

### Exploit Chain

1. Register an account, get your `csrf_token` cookie
2. Create a note with HTML that:
   - Sets a new `csrf_token` cookie via `<img src="http://api.ctf.local/cookie/set?csrf_token=YOUR_TOKEN">`
   - Redirects via JS to `http://app.ctf.local/change-password?password=NEWPASS&csrf_token=YOUR_TOKEN`
3. Submit the note URL to the admin bot (POST to `http://localhost:8888/report`)
4. Admin visits the note → cookie tossed → password changed
5. Log in as `admin` with the new password
6. Visit `/flag` to read the flag

## Hint

Why does the app use `getlist()` instead of `get()` for the CSRF token check?

## Flag

```
CTF{cs1rf_c00k1e_t0ss1ng_ftw}
```

## License

MIT
