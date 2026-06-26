# Candidate Portal — Take-Home

A tiny Express API for managing tasks. Your goal: review the code in
`src/app.js` and propose improvements covering correctness,
idiomatic style, and any security concerns you spot.

## Setup

```bash
npm install
npm start
```

The server listens on port 3000.

## Endpoints

| Method | Path        | Description                            |
|--------|-------------|----------------------------------------|
| GET    | `/tasks`    | List all tasks                         |
| POST   | `/tasks`    | Create a task `{ "title": string }`    |
| DELETE | `/tasks/:id`| Remove a task by id                    |

## What we're evaluating

- Did you read the code carefully before suggesting changes?
- Are your suggestions specific and minimal, or sweeping rewrites?
- Did you call out any security-relevant behavior?
