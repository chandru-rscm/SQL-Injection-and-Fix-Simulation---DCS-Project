from flask import Flask, request, jsonify, render_template_string
import sqlite3
import os

app = Flask(__name__)
DB_PATH = "/tmp/demo.db"

# ── bootstrap DB ──────────────────────────────────────────────────────────────
def init_db():
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    cur.execute("DROP TABLE IF EXISTS users")
    cur.execute("""
        CREATE TABLE users (
            id       INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            password TEXT NOT NULL,
            role     TEXT NOT NULL
        )
    """)
    cur.executemany(
        "INSERT INTO users (username, password, role) VALUES (?, ?, ?)",
        [
            ("alice",  "secret123",  "user"),
            ("bob",    "qwerty456",  "user"),
            ("admin",  "adm1nP@ss",  "admin"),
        ]
    )
    con.commit()
    con.close()

init_db()

# ── HTML (single-page, all CSS + JS inline) ───────────────────────────────────
HTML = r"""
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>SQL Injection — Attack vs Defence</title>
<link href="https://fonts.googleapis.com/css2?family=Share+Tech+Mono&family=Syne:wght@400;700;800&display=swap" rel="stylesheet">
<style>
  :root {
    --bg:      #0a0a0f;
    --surface: #111118;
    --border:  #1e1e2e;
    --accent-r:#ff3c5f;
    --accent-g:#00e5a0;
    --text:    #e2e2f0;
    --muted:   #5a5a7a;
    --mono:    'Share Tech Mono', monospace;
    --sans:    'Syne', sans-serif;
  }

  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

  body {
    background: var(--bg);
    color: var(--text);
    font-family: var(--sans);
    min-height: 100vh;
    padding: 2rem 1rem 4rem;
  }

  /* ── grid noise overlay ── */
  body::before {
    content: '';
    position: fixed; inset: 0;
    background-image:
      repeating-linear-gradient(0deg,   transparent, transparent 39px, rgba(255,255,255,.025) 40px),
      repeating-linear-gradient(90deg,  transparent, transparent 39px, rgba(255,255,255,.025) 40px);
    pointer-events: none; z-index: 0;
  }

  .wrap { max-width: 1060px; margin: 0 auto; position: relative; z-index: 1; }

  /* ── header ── */
  header { text-align: center; margin-bottom: 3rem; }
  header .eyebrow {
    font-family: var(--mono);
    font-size: .75rem;
    letter-spacing: .25em;
    color: var(--accent-r);
    text-transform: uppercase;
    margin-bottom: .5rem;
  }
  header h1 {
    font-size: clamp(1.8rem, 5vw, 3rem);
    font-weight: 800;
    line-height: 1.1;
  }
  header h1 span.bad  { color: var(--accent-r); }
  header h1 span.good { color: var(--accent-g); }
  header p {
    margin-top: .75rem;
    color: var(--muted);
    font-size: .95rem;
    font-family: var(--mono);
  }

  /* ── two-column layout ── */
  .cols {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 1.5rem;
  }
  @media (max-width: 680px) { .cols { grid-template-columns: 1fr; } }

  /* ── panel ── */
  .panel {
    border: 1px solid var(--border);
    border-radius: 12px;
    overflow: hidden;
    background: var(--surface);
  }
  .panel-head {
    display: flex; align-items: center; gap: .75rem;
    padding: 1rem 1.25rem;
    border-bottom: 1px solid var(--border);
  }
  .badge {
    font-family: var(--mono);
    font-size: .65rem;
    letter-spacing: .15em;
    text-transform: uppercase;
    padding: .2rem .6rem;
    border-radius: 4px;
    font-weight: 700;
  }
  .badge-vuln { background: rgba(255,60,95,.15); color: var(--accent-r); border: 1px solid rgba(255,60,95,.3); }
  .badge-safe { background: rgba(0,229,160,.12); color: var(--accent-g); border: 1px solid rgba(0,229,160,.25); }
  .panel-head h2 { font-size: 1rem; font-weight: 700; }

  .panel-body { padding: 1.25rem; }

  /* ── form ── */
  label {
    display: block;
    font-family: var(--mono);
    font-size: .7rem;
    letter-spacing: .12em;
    text-transform: uppercase;
    color: var(--muted);
    margin-bottom: .35rem;
    margin-top: .9rem;
  }
  label:first-of-type { margin-top: 0; }

  input[type=text], input[type=password] {
    width: 100%;
    background: var(--bg);
    border: 1px solid var(--border);
    border-radius: 6px;
    color: var(--text);
    font-family: var(--mono);
    font-size: .9rem;
    padding: .6rem .85rem;
    transition: border-color .2s;
    outline: none;
  }
  input:focus { border-color: var(--muted); }

  button {
    margin-top: 1.1rem;
    width: 100%;
    padding: .7rem 1rem;
    border: none; border-radius: 6px;
    font-family: var(--sans);
    font-size: .9rem;
    font-weight: 700;
    cursor: pointer;
    letter-spacing: .04em;
    transition: opacity .15s, transform .1s;
  }
  button:active { transform: scale(.98); }
  .btn-vuln { background: var(--accent-r); color: #fff; }
  .btn-safe  { background: var(--accent-g); color: #0a0a0f; }

  /* ── hint chips ── */
  .hints {
    margin-top: 1rem;
    display: flex; flex-wrap: wrap; gap: .4rem;
  }
  .hint {
    font-family: var(--mono);
    font-size: .7rem;
    padding: .25rem .6rem;
    border-radius: 4px;
    background: rgba(255,255,255,.05);
    border: 1px solid var(--border);
    color: var(--muted);
    cursor: pointer;
    transition: background .15s;
  }
  .hint:hover { background: rgba(255,255,255,.1); color: var(--text); }

  /* ── result box ── */
  .result-box {
    margin-top: 1.1rem;
    border-radius: 8px;
    padding: .9rem 1rem;
    font-family: var(--mono);
    font-size: .82rem;
    line-height: 1.6;
    min-height: 3.5rem;
    border: 1px solid transparent;
    transition: all .25s;
    display: none;
  }
  .result-box.show { display: block; }
  .result-box.success-v {
    background: rgba(255,60,95,.1);
    border-color: rgba(255,60,95,.35);
    color: var(--accent-r);
  }
  .result-box.success-s {
    background: rgba(0,229,160,.08);
    border-color: rgba(0,229,160,.3);
    color: var(--accent-g);
  }
  .result-box.fail {
    background: rgba(90,90,120,.12);
    border-color: var(--border);
    color: var(--muted);
  }

  /* ── query display ── */
  .query-wrap {
    margin-top: 1rem;
    background: var(--bg);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: .8rem 1rem;
  }
  .query-label {
    font-family: var(--mono);
    font-size: .65rem;
    letter-spacing: .15em;
    text-transform: uppercase;
    color: var(--muted);
    margin-bottom: .45rem;
  }
  .query-code {
    font-family: var(--mono);
    font-size: .78rem;
    color: #a9b1d6;
    white-space: pre-wrap;
    word-break: break-all;
  }
  .query-code .inject { color: var(--accent-r); font-weight: 700; }
  .query-code .safe-ph { color: var(--accent-g); }

  /* ── explanation section ── */
  .explain {
    margin-top: 2.5rem;
    border: 1px solid var(--border);
    border-radius: 12px;
    background: var(--surface);
    padding: 1.5rem 1.75rem;
  }
  .explain h3 {
    font-size: 1.1rem; font-weight: 800;
    margin-bottom: 1rem;
    display: flex; align-items: center; gap: .5rem;
  }
  .explain-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 1.25rem;
  }
  @media (max-width: 680px) { .explain-grid { grid-template-columns: 1fr; } }
  .ex-card {
    border-radius: 8px;
    padding: 1rem 1.1rem;
    border: 1px solid var(--border);
  }
  .ex-card h4 { font-size: .85rem; font-weight: 700; margin-bottom: .5rem; }
  .ex-card p  { font-size: .82rem; color: var(--muted); line-height: 1.65; font-family: var(--mono); }
  .ex-card code {
    background: rgba(255,255,255,.06);
    padding: .1rem .35rem;
    border-radius: 3px;
    font-size: .78rem;
  }
  .ex-card.bad  { background: rgba(255,60,95,.05); }
  .ex-card.good { background: rgba(0,229,160,.04); }

  /* ── users table ── */
  .db-section { margin-top: 2rem; }
  .db-section summary {
    cursor: pointer;
    font-family: var(--mono);
    font-size: .78rem;
    color: var(--muted);
    letter-spacing: .1em;
    padding: .5rem 0;
  }
  .db-section summary:hover { color: var(--text); }
  table { width: 100%; border-collapse: collapse; margin-top: .75rem; }
  th, td {
    text-align: left;
    padding: .5rem .75rem;
    font-family: var(--mono);
    font-size: .78rem;
    border-bottom: 1px solid var(--border);
  }
  th { color: var(--muted); font-size: .68rem; letter-spacing: .12em; text-transform: uppercase; }
  td { color: var(--text); }
  tr:last-child td { border-bottom: none; }

  /* ── spinner ── */
  .spin {
    display: inline-block;
    width: 14px; height: 14px;
    border: 2px solid rgba(255,255,255,.15);
    border-top-color: currentColor;
    border-radius: 50%;
    animation: spin .6s linear infinite;
    vertical-align: middle;
    margin-right: .4rem;
  }
  @keyframes spin { to { transform: rotate(360deg); } }
</style>
</head>
<body>
<div class="wrap">

  <header>
    <div class="eyebrow">DCS Lab Demo · SQL Injection</div>
    <h1><span class="bad">Attack</span> vs <span class="good">Defence</span></h1>
    <p>Vulnerable query &nbsp;←→&nbsp; Parameterised prepared statement</p>
  </header>

  <div class="cols">

    <!-- ── VULNERABLE PANEL ── -->
    <div class="panel">
      <div class="panel-head">
        <span class="badge badge-vuln">⚠ Vulnerable</span>
        <h2>String Concatenation</h2>
      </div>
      <div class="panel-body">
        <label>Username</label>
        <input id="v-user" type="text" placeholder="alice" autocomplete="off">

        <label>Password</label>
        <input id="v-pass" type="text" placeholder="try an injection payload">

        <div class="hints">
          <span class="hint" onclick="injectHint(&#34;' OR '1'='1&#34;)">
            ' OR '1'='1
          </span>
          <span class="hint" onclick="injectHint(&#34;' OR 1=1--&#34;)">
            ' OR 1=1--
          </span>
          <span class="hint" onclick="injectHint(&#34;admin'--&#34;)">
            admin'--
          </span>
        </div>

        <button class="btn-vuln" onclick="tryLogin('vuln')">
          Attempt Login
        </button>

        <div id="v-result" class="result-box"></div>
        <div id="v-query" class="query-wrap" style="display:none">
          <div class="query-label">Query executed</div>
          <div id="v-query-code" class="query-code"></div>
        </div>
      </div>
    </div>

    <!-- ── SECURE PANEL ── -->
    <div class="panel">
      <div class="panel-head">
        <span class="badge badge-safe">✓ Secure</span>
        <h2>Prepared Statement</h2>
      </div>
      <div class="panel-body">
        <label>Username</label>
        <input id="s-user" type="text" placeholder="alice" autocomplete="off">

        <label>Password</label>
        <input id="s-pass" type="text" placeholder="same payloads won't work here">

        <div class="hints">
          <span class="hint" onclick="injectHintSecure(&#34;' OR '1'='1&#34;)">
            ' OR '1'='1
          </span>
          <span class="hint" onclick="injectHintSecure(&#34;' OR 1=1--&#34;)">
            ' OR 1=1--
          </span>
          <span class="hint" onclick="injectHintSecure(&#34;admin'--&#34;)">
            admin'--
          </span>
        </div>

        <button class="btn-safe" onclick="tryLogin('secure')">
          Attempt Login
        </button>

        <div id="s-result" class="result-box"></div>
        <div id="s-query" class="query-wrap" style="display:none">
          <div class="query-label">Query executed</div>
          <div id="s-query-code" class="query-code"></div>
        </div>
      </div>
    </div>
  </div>

  <!-- ── EXPLANATION ── -->
  <div class="explain">
    <h3>📖 How it works</h3>
    <div class="explain-grid">
      <div class="ex-card bad">
        <h4 style="color:var(--accent-r)">❌ Vulnerable — string concatenation</h4>
        <p>
          The app builds the SQL query by directly gluing user input into the string:<br><br>
          <code>"SELECT * FROM users WHERE username='" + user + "' AND password='" + pw + "'"</code><br><br>
          Entering <code>' OR '1'='1</code> as the password turns the condition always-true,
          bypassing authentication entirely.
        </p>
      </div>
      <div class="ex-card good">
        <h4 style="color:var(--accent-g)">✅ Secure — prepared statement</h4>
        <p>
          The query uses placeholders: <code>WHERE username=? AND password=?</code><br><br>
          The DB driver sends the query and the values <em>separately</em>.
          The <code>'</code> in a payload is treated as a literal character, not SQL syntax —
          so injections are structurally impossible.
        </p>
      </div>
    </div>

    <div class="db-section">
      <details>
        <summary>▶ Show demo database (3 users)</summary>
        <table>
          <thead><tr><th>ID</th><th>Username</th><th>Password</th><th>Role</th></tr></thead>
          <tbody>
            <tr><td>1</td><td>alice</td><td>secret123</td><td>user</td></tr>
            <tr><td>2</td><td>bob</td><td>qwerty456</td><td>user</td></tr>
            <tr><td>3</td><td>admin</td><td>adm1nP@ss</td><td>admin</td></tr>
          </tbody>
        </table>
      </details>
    </div>
  </div>

</div>

<script>
function injectHint(val) {
  document.getElementById('v-user').value = 'anything';
  document.getElementById('v-pass').value = val;
}
function injectHintSecure(val) {
  document.getElementById('s-user').value = 'anything';
  document.getElementById('s-pass').value = val;
}

async function tryLogin(mode) {
  const prefix  = mode === 'vuln' ? 'v' : 's';
  const endpoint = mode === 'vuln' ? '/login/vulnerable' : '/login/secure';

  const username = document.getElementById(prefix + '-user').value;
  const password = document.getElementById(prefix + '-pass').value;

  const resBox   = document.getElementById(prefix + '-result');
  const queryBox = document.getElementById(prefix + '-query');
  const queryCode = document.getElementById(prefix + '-query-code');

  resBox.className = 'result-box show';
  resBox.innerHTML = '<span class="spin"></span> Querying…';

  const resp = await fetch(endpoint, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, password })
  });
  const data = await resp.json();

  // result
  if (data.success) {
    resBox.className = mode === 'vuln'
      ? 'result-box show success-v'
      : 'result-box show success-s';
    resBox.innerHTML = data.success
      ? `✓ Logged in as <strong>${data.user}</strong> (role: ${data.role})`
      : '';
  } else {
    resBox.className = 'result-box show fail';
    resBox.innerHTML = '✗ ' + (data.error || 'Invalid credentials');
  }

  // query
  queryBox.style.display = 'block';
  queryCode.innerHTML = data.query_display || '';
}
</script>
</body>
</html>
"""

# ── routes ────────────────────────────────────────────────────────────────────
@app.route("/")
def index():
    return render_template_string(HTML)


@app.route("/login/vulnerable", methods=["POST"])
def login_vulnerable():
    """Deliberately insecure — string concatenation."""
    body     = request.get_json()
    username = body.get("username", "")
    password = body.get("password", "")

    # build the raw (dangerous) query string
    raw_query = (
        f"SELECT * FROM users WHERE username='{username}' AND password='{password}'"
    )

    # highlight injected parts for display
    def highlight(q, u, p):
        q_display = q.replace(
            u, f'<span class="inject">{u}</span>', 1
        ).replace(
            p, f'<span class="inject">{p}</span>', 1
        )
        return q_display

    query_display = highlight(raw_query, username, password)

    try:
        con = sqlite3.connect(DB_PATH)
        cur = con.cursor()
        cur.execute(raw_query)          # ← no sanitisation
        row = cur.fetchone()
        con.close()
    except Exception as e:
        return jsonify({
            "success": False,
            "error": f"DB error: {str(e)}",
            "query_display": query_display
        })

    if row:
        return jsonify({
            "success": True,
            "user": row[1],
            "role": row[3],
            "query_display": query_display
        })
    return jsonify({
        "success": False,
        "error": "No matching user found.",
        "query_display": query_display
    })


@app.route("/login/secure", methods=["POST"])
def login_secure():
    """Secure — parameterised prepared statement."""
    body     = request.get_json()
    username = body.get("username", "")
    password = body.get("password", "")

    parameterised = "SELECT * FROM users WHERE username=? AND password=?"
    query_display = (
        f'<span class="safe-ph">SELECT * FROM users WHERE username=? AND password=?</span>\n'
        f'<span style="color:var(--muted)">-- bound values: ({repr(username)}, {repr(password)})</span>'
    )

    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    cur.execute(parameterised, (username, password))   # ← safe
    row = cur.fetchone()
    con.close()

    if row:
        return jsonify({
            "success": True,
            "user": row[1],
            "role": row[3],
            "query_display": query_display
        })
    return jsonify({
        "success": False,
        "error": "No matching user found.",
        "query_display": query_display
    })


if __name__ == "__main__":
    app.run(debug=True, port=5050)
