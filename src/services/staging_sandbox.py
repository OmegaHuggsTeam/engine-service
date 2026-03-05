"""
Staging Sandbox - Mock server local para testes E2E.
Simula formularios HTML dos providers (Google, GitHub, Groq).
Roda em localhost:9090.
"""

from fastapi import FastAPI, Form
from fastapi.responses import HTMLResponse

app = FastAPI(title="Identity Staging Sandbox", version="1.0")


# ---- Google Mock ----

@app.get("/mock/google", response_class=HTMLResponse)
async def google_login_form():
    return """<!DOCTYPE html>
<html><body>
<h1>Google Account (Mock)</h1>
<form id="login-form" action="/mock/google/submit" method="post">
  <input id="email-input" name="email" type="email" placeholder="Email" />
  <input id="display-name-input" name="display_name" type="text" placeholder="Display Name" />
  <button id="submit-btn" type="submit">Sign In</button>
</form>
</body></html>"""


@app.post("/mock/google/submit", response_class=HTMLResponse)
async def google_submit(email: str = Form(""), display_name: str = Form("")):
    return f"""<!DOCTYPE html>
<html><body>
<div class="success-msg">Account created for {email}</div>
<p>Display name: {display_name}</p>
</body></html>"""


# ---- GitHub Mock ----

@app.get("/mock/github", response_class=HTMLResponse)
async def github_signup_form():
    return """<!DOCTYPE html>
<html><body>
<h1>GitHub Signup (Mock)</h1>
<form id="signup-form" action="/mock/github/submit" method="post">
  <input id="username-input" name="username" type="text" placeholder="Username" />
  <input id="email-input" name="email" type="email" placeholder="Email" />
  <button id="create-account-btn" type="submit">Create Account</button>
</form>
</body></html>"""


@app.post("/mock/github/submit", response_class=HTMLResponse)
async def github_submit(username: str = Form(""), email: str = Form("")):
    return f"""<!DOCTYPE html>
<html><body>
<div class="welcome-msg">Welcome {username}!</div>
<p>Email: {email}</p>
</body></html>"""


# ---- Groq Mock ----

@app.get("/mock/groq", response_class=HTMLResponse)
async def groq_api_keys():
    return """<!DOCTYPE html>
<html><body>
<h1>Groq API Keys (Mock)</h1>
<div id="api-keys">
  <p>Your API Keys:</p>
  <div id="new-key-value">gsk_mock_test_key_1234567890abcdef</div>
</div>
</body></html>"""


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=9090)
