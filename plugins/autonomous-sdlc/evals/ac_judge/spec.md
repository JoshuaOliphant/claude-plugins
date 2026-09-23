## Acceptance Criteria: User Authentication

### AC-1: Successful login
**Given** a registered user with email "alice@example.com" and a valid password
**When** the user submits the login form with correct credentials
**Then** the user is redirected to the dashboard
  and a session token is created

### AC-2: Failed login with wrong password
**Given** a registered user with email "alice@example.com"
**When** the user submits the login form with an incorrect password
**Then** the system displays "Invalid credentials"
  and the user remains on the login page
  and the failed attempt is logged

### AC-3: Account lockout after repeated failures
**Given** a registered user who has failed login 4 times
**When** the user fails login a 5th time
**Then** the account is locked for 15 minutes
  and the system displays "Account locked. Try again in 15 minutes."

### AC-4: Password reset flow
**Given** a registered user on the login page
**When** the user clicks "Forgot Password" and enters their email
**Then** a password reset email is sent
  and the system displays "Check your email for reset instructions"
