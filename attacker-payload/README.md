# attacker-payload — the off-repo payload (Lab 1A)

This is the **attacker-controlled** side of Lab 1A. In the real attack — and
in the live demo — **none of this is in the repo a candidate clones**. That's
the whole point: you can `grep` `assessment-1/` for `fs.writeFileSync`,
`child_process`, `exec`, the marker path, anything — and find nothing. The
malicious behaviour lives here, on the attacker's server.

It's reproduced in this repo only so you can read the full chain after the
talk. **Defanged:** it writes a marker file to `/tmp/labs/` and makes no
outbound network calls. Still — run it only in a throwaway VM/container.

## The chain

1. `assessment-1/server/config/config.js` holds a hex string that looks like
   a `tenantId`. Decoded, it's `http://bsidesworkshop.vibecheck:8080/payload`.
2. `auth.controller.js` fetches that URL and passes the response into
   `logFormatter()`.
3. `logFormatter.js` compiles the fetched string with
   `new Function('loadModule', template)` and calls it with `require` —
   so the remote snippet gets full Node capabilities (`fs`, `os`, `process`).

## Files

| File | Role |
|---|---|
| `server.py` | The "C2". Serves `payload.js` as `{"snippet": "..."}` at `http://127.0.0.1:8080/payload`. Re-reads on every request, so editing the payload needs no restart. |
| `payload.js` | The fetched snippet. `loadModule` is the injected `require`; it reads env (incl. a fake `SUPER_SECRET_API_KEY`) and writes a marker to `/tmp/labs/`. A real stealer would POST it to the attacker instead. |

## Detonate (sandbox only)

```bash
# add the fake C2 hostname (one-time, in your sandbox)
echo '127.0.0.1 bsidesworkshop.vibecheck' | sudo tee -a /etc/hosts

python3 server.py &                 # start the C2 on 127.0.0.1:8080
cd ../assessment-1 && npm install && SUPER_SECRET_API_KEY=demo npm start
# hit any endpoint, then look in /tmp/labs/
```
