# Audit Log Service — Take-Home

A tiny Express API for querying an in-memory audit log with offset
+ limit pagination. Your goal: review the code in `src/app.js` and
propose improvements covering correctness, idiomatic style, and any
security concerns you spot.

## Setup

```bash
npm install
npm start
```

The server listens on port 3005.

## Endpoints

| Method | Path           | Description                                       |
|--------|----------------|---------------------------------------------------|
| POST   | `/events`      | Append an event `{ "kind": str, "actor": str }`   |
| GET    | `/events`      | List events (supports `?offset=N&limit=N`)        |

## What we're evaluating

- Did you read the code carefully before suggesting changes?
- Are your suggestions specific and minimal, or sweeping rewrites?
- Did you call out any security-relevant behavior?
