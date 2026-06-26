# Candidate Portal Challenge — Take-Home

Thanks for taking the time to complete this backend technical screen.

## Stack

- Node.js / Express
- In-memory user store (no database setup needed)
- JWT for session tokens

## Task

The `POST /auth/login` endpoint is returning **HTTP 500** for valid
credentials. The endpoint should return a `200` with a JWT token on
success and a `401` on bad credentials. Find the bug and fix it.

Acceptance criteria:

1. `POST /auth/login` returns `200 { token: "..." }` for the seeded
   user (`alice@example.com` / `password123`).
2. `POST /auth/login` returns `401` for a wrong password.
3. Existing routes (`/auth/register`, `/users/:id`) continue to work.

## Setup

```bash
npm install
npm start
```

The server listens on port 3000.

## Submitting

Please send back a short summary of your fix, the exact `curl` command
you used to verify, and a link to your fork or a zip.

Aim for 30–45 minutes. Reach out if anything is unclear.
