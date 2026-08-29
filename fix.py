import re

with open('frontend/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Try to extract the main portion
match = re.search(r'<main id="top" class="shell">.*', content, re.DOTALL)
if match:
    main_content = match.group(0)
else:
    match2 = re.search(r'      <section class="intro">.*', content, re.DOTALL)
    if match2:
        main_content = '<main id="top" class="shell">\n' + match2.group(0)
    else:
        main_content = content

new_html = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>EcoTrack AI</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Space+Grotesk:wght@500;600;700&display=swap" rel="stylesheet">
  <link rel="stylesheet" href="styles.css">
  <link rel="stylesheet" href="auth.css">
  <link rel="stylesheet" href="location.css">
  <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" crossorigin="">
</head>
<body>
  <div id="login-screen" class="login-screen intro-mode">
    <div class="login-box">
      <div class="auth-header-wrapper">
        <h2 id="auth-title">Register now</h2>
        <p id="auth-subtitle">Secure your spot in EcoTrack AI</p>
      </div>
      
      <form id="auth-form" class="auth-form">
        <input type="hidden" id="auth-mode" value="register">
        
        <div class="input-group" id="group-name">
          <input id="auth-name" type="text" placeholder="Your name" autocomplete="name" required>
        </div>
        
        <div class="input-group" id="group-email">
          <input id="auth-email" type="email" placeholder="Email address" autocomplete="email" required>
        </div>
        
        <div class="input-group" id="group-password">
          <input id="auth-password" type="password" placeholder="Password (5+ characters)" autocomplete="new-password" minlength="5" required>
          <div id="password-rules" class="password-rules" style="font-size: 11px; color: rgba(255,255,255,0.7); margin-top: 4px;" hidden>
            Requires 12+ chars, mix of upper/lower, numbers, and symbols (!@#$*). Avoid personal data or simple swaps.
          </div>
        </div>
        
        <div class="input-group" id="group-captcha">
          <div id="captcha-group" class="captcha-group">
            <span id="captcha-question">Loading...</span>
            <input id="auth-captcha-answer" type="text" placeholder="Captcha Answer" required>
            <button type="button" id="refresh-captcha" aria-label="Refresh Captcha">↻</button>
          </div>
        </div>
        
        <div class="input-group" id="group-otp" hidden>
          <input id="auth-otp" type="text" placeholder="Enter 6-digit OTP" minlength="6" maxlength="6" autocomplete="one-time-code">
        </div>

        <button id="auth-submit-btn" class="primary-button green-button" type="submit">Next</button>
        
        <p class="form-message" id="auth-message" role="status"></p>
        
        <div class="auth-links">
          <a href="#" id="link-login">Already have an account? Sign in</a>
          <a href="#" id="link-register" hidden>Need an account? Register now</a>
          <a href="#" id="link-forgot">Forgot password?</a>
        </div>
      </form>
    </div>
  </div>

  <div id="app-wrapper" hidden>
    <header class="topbar">
      <a class="brand" href="#top" aria-label="EcoTrack AI home"><span class="brand-mark">E</span><span>EcoTrack <em>AI</em></span></a>
      <div class="session"><span id="session-label">Not signed in</span><button id="logout" class="logout-button" type="button" hidden>Sign out</button></div>
    </header>

""" + main_content

with open('frontend/index.html', 'w', encoding='utf-8') as f:
    f.write(new_html)

print("File updated.")
