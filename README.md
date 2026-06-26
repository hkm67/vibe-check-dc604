# vibe-check-dc604 — Lab 1 Assessments

Read-only source for the two "take-home assessment" repos from the talk
**Vibe Check: Exploiting Trust — from Developers to AI agents** (DC604,
June 2026).

These are the exact files a candidate would receive in the fake-recruiter
scenario from the talk. They are published here so attendees can read the
code at their own pace afterwards.

> ⚠️ **Don't run these on your host machine.** The whole point of the talk
> is that *opening or running an untrusted repo can compromise you*. These
> labs are **defanged** — the only side effect is a marker file written to
> `/tmp/labs/`, and there are no real network exfil targets — but treat them
> as live malware and detonate only inside a throwaway VM or container.

## What's here

| Folder | Lab | Trust vector |
|---|---|---|
| `assessment-1/` | **Lab 1A** | Running `npm start` executes repo code. The Express app fetches a remote snippet and compiles it with `new Function`, handing it `require` — full Node capabilities from an off-repo payload. |
| `assessment-2/` | **Lab 1B** | **Workspace Trust.** `.vscode/tasks.json` with `runOn: folderOpen` auto-runs a script the moment you open the folder in an editor that doesn't enforce trust (Cursor's default as of the talk). No command needed. |
| `attacker-payload/` | **Lab 1A (off-repo)** | The attacker-controlled C2 stub + `payload.js` that `assessment-1` fetches. **Not** part of the repo a candidate clones — included here so the full chain is readable. See its [README](attacker-payload/README.md). |

Each repo ships a plausible "fix this bug" task (`README.md` inside each
folder). The bugs are real and fixable — but the attack lives elsewhere:

- **Lab 1A:** a hex string in `assessment-1/server/config/config.js` that
  looks like a tenant ID decodes to a URL. Grep the repo for the malicious
  behaviour and you find nothing — it lives on the attacker's server (the
  `attacker-payload/` folder here reproduces it so you can read it).
- **Lab 1B:** you don't execute anything. Opening the folder is enough.

`reset-assessment-1.sh` restores `assessment-1/` to a clean state between
runs (kills the server, removes `node_modules`).

## Safety boundary

The boundary is **the sandbox you run them in**, not the lab code. Payloads
write marker files to `/tmp/labs/` and make no outbound network calls beyond
loopback. See the talk for the full walkthrough and the original workshop
container at <https://github.com/hkm67/vibe-check-workshop>.

## License

MIT — see [`LICENSE`](LICENSE).
