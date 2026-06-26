# Rate Limit Proxy — Take-Home

A tiny Express middleware proxy that rate-limits incoming requests
per API key. Your goal: review the code in `src/app.js` and propose
improvements covering correctness, idiomatic style, and any security
concerns you spot.

## Setup

```bash
npm install
npm start
```

The server listens on port 3004.

## Endpoints

| Method | Path        | Description                          |
|--------|-------------|--------------------------------------|
| GET    | `/limit/:key` | Check rate-limit state for an API key |
| POST   | `/limit/:key` | Record a hit against an API key       |

## What we're evaluating

- Did you read the code carefully before suggesting changes?
- Are your suggestions specific and minimal, or sweeping rewrites?
- Did you call out any security-relevant behavior?

## License

This project is distributed under the **GNU GPL v3** (see `LICENSE`).
The license includes additional terms under GPL §7.
