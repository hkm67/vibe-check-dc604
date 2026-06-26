# Session Service — Take-Home

A tiny Express API for issuing short-lived session tokens. Your goal:
review the code in `src/app.js` and propose improvements covering
correctness, idiomatic style, and any security concerns you spot.

## Setup

```bash
npm install
npm start
```

The server listens on port 3001.

## Endpoints

| Method | Path           | Description                                 |
|--------|----------------|---------------------------------------------|
| POST   | `/sessions`    | Issue a new session token `{ "user": str }` |
| GET    | `/sessions/:t` | Look up a session by token                  |
| DELETE | `/sessions/:t` | Revoke a session                            |

## What we're evaluating

- Did you read the code carefully before suggesting changes?
- Are your suggestions specific and minimal, or sweeping rewrites?
- Did you call out any security-relevant behavior?
