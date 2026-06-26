# Webhook Router — Take-Home

A tiny Express service that accepts incoming webhooks and queues
them for delivery. Your goal: review the code in `src/app.js` and
propose improvements covering correctness, idiomatic style, and any
security concerns you spot.

## Setup

```bash
npm install
npm start
```

The server listens on port 3003.

## Endpoints

| Method | Path        | Description                                       |
|--------|-------------|---------------------------------------------------|
| POST   | `/webhooks` | Accept a webhook `{ "event": str, "data": obj }`  |
| GET    | `/webhooks` | List queued webhooks                              |

## What we're evaluating

- Did you read the code carefully before suggesting changes?
- Are your suggestions specific and minimal, or sweeping rewrites?
- Did you call out any security-relevant behavior?
