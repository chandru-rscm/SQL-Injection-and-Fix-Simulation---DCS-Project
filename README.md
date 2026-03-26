# SQL Injection Demo — DCS Assignment #11

## What this demonstrates
Two login endpoints side-by-side:
- `/login/vulnerable` — uses **string concatenation** (injectable)
- `/login/secure`    — uses **prepared statements** (injection-proof)

## Setup

```bash
pip install flask
python app.py
```
Then open http://localhost:5050 in your browser.

## Demo steps for viva

### Step 1 — Normal login (both panels work)
- Username: `alice`  Password: `secret123`  → Login succeeds on both

### Step 2 — SQL Injection on VULNERABLE panel
- Click any payload chip, e.g. **`' OR '1'='1`**
- Hit "Attempt Login"
- Result: **Logged in as alice** even with wrong password
- The executed query is shown below — notice how the payload breaks out of the string

### Step 3 — Same payload on SECURE panel
- Click the same chip
- Hit "Attempt Login"  
- Result: **Invalid credentials** — injection is blocked
- The query shows `?` placeholders — the payload is treated as data, not code

## Why it works / how to explain it

| | Vulnerable | Secure |
|---|---|---|
| Query building | `"WHERE user='" + input + "'"` | `"WHERE user=?"` |
| Input handling | Concatenated into SQL string | Passed separately to DB driver |
| `' OR '1'='1` effect | Modifies query logic | Treated as a literal string |
| Fix | Don't do this | **Always use parameterised queries** |

## Files
- `app.py` — Flask app (all logic + UI in one file)
- `demo.db` — auto-created in /tmp at runtime
