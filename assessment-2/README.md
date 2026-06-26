# Frontend Interview Assessment

Thanks for taking the time to complete this take-home.

## Stack

- Node.js (any LTS)
- No frameworks, no build step — the file you care about is `src/app.js`.

## Task

The `greeting()` utility in `src/app.js` is used by the onboarding
splash page. It currently **crashes** when the candidate name is not
supplied:

```bash
$ node src/app.js Alice
Hello, Alice!
$ node src/app.js
TypeError: Cannot read properties of undefined (reading 'trim')
```

Make it fall back to a safe default (`"candidate"`) when no argument
is passed.

### Acceptance criteria

1. `node src/app.js Alice` → `Hello, Alice!`
2. `node src/app.js` → `Hello, candidate!`
3. `node src/app.js "  Bob  "` → `Hello, Bob!` (existing trim behavior preserved)

## Submitting

Send back:

- the file and line you changed,
- a short note on the root cause,
- the `node` command(s) you used to verify.

Aim for 15–30 minutes. Reach out if anything is unclear.
