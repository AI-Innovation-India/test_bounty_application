# Skill: Authentication & Security Testing

## Domain
Login systems, user registration, password management, SSO, 2FA, session management

## Trigger Keywords
login, signin, sign-in, register, signup, sign-up, auth, password, forgot, reset, 2fa, otp, sso, token, session, logout, account, credential

## Critical Test Areas

### Login
- Valid credentials → redirect to dashboard/home
- Invalid password → error message (do NOT reveal which field is wrong for security)
- Non-existent email → same generic error as wrong password (prevents user enumeration)
- Empty form submission → field-level validation errors
- Email format validation (missing @, no domain)
- Case sensitivity: email should be case-insensitive, password case-sensitive
- Whitespace trimming: leading/trailing spaces in email should be trimmed

### Account Lockout (Security Critical)
- N consecutive failed attempts (typically 5) → account temporarily locked
- Lockout message does not reveal lockout threshold
- Lockout resets after cooldown period or manual unlock
- Valid login after lockout (once reset) works correctly

### Registration
- All required fields validated
- Email uniqueness enforced (duplicate email shows clear error)
- Password strength requirements enforced (length, complexity)
- Password and confirm-password must match
- Email verification flow (if applicable): verify link works, expired link handled
- Terms acceptance required before submission

### Password Reset
- Valid email → reset email sent (do NOT confirm if email exists for security)
- Reset link is single-use (second use should fail)
- Reset link expires (test with expired token)
- New password meets strength requirements
- After reset, old password no longer works
- After reset, existing sessions should be invalidated

### Session Management
- Session expires after configured timeout (inactivity)
- Logout clears session server-side (token blacklisted)
- After logout, browser back button should not reveal protected content
- Concurrent login behaviour (single session vs. multi-session)
- Remember me: session persists across browser close
- Session cookie has Secure, HttpOnly, SameSite flags

### Two-Factor Authentication (2FA)
- OTP sent to correct destination (email/SMS/app)
- Expired OTP rejected
- Wrong OTP rejected with counter
- Bypass attempt (skipping 2FA step directly) blocked
- Backup codes work

### OAuth / SSO
- "Login with Google/Microsoft" redirect works
- Successful OAuth → user created/linked in system
- OAuth failure → user-friendly error
- Account linking: existing email + OAuth from same email

## Security Anti-patterns to Test
- Verify login endpoints have rate limiting (429 after many requests)
- JWT tokens: tampered tokens rejected
- CSRF protection on login form
- Password not visible in page source or network response

## Common Selector Patterns
- Email: `#email`, `input[name='email']`, `input[type='email']`
- Password: `#password`, `input[name='password']`, `input[type='password']`
- Submit: `button[type='submit']`, `.login-btn`, `input[type='submit']`
- Error: `.error-message`, `.alert-danger`, `[role='alert']`, `.validation-summary-errors`
- Logout: `a:has-text('Logout')`, `[href*='logout']`, `.ico-logout`
