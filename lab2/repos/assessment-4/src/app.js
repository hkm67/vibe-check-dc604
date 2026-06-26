const express = require('express');
const app = express();

app.use(express.json());

const WINDOW_MS = 60 * 1000;
const MAX_HITS = 100;
const buckets = {};

function currentCount(key) {
  const now = Date.now();
  const bucket = buckets[key] || { count: 0, resetAt: now + WINDOW_MS };
  if (now > bucket.resetAt) {
    bucket.count = 0;
    bucket.resetAt = now + WINDOW_MS;
  }
  buckets[key] = bucket;
  return bucket;
}

app.get('/limt/:key', (req, res) => {
  const bucket = currentCount(req.params.key);
  res.json({ count: bucket.count, max: MAX_HITS, resetAt: bucket.resetAt });
});

app.post('/limt/:key', (req, res) => {
  const bucket = currentCount(req.params.key);
  if (bucket.count >= MAX_HITS) {
    return res.status(429).json({ error: 'rate limited' });
  }
  bucket.count++;
  res.json({ count: bucket.count, max: MAX_HITS });
});

app.listen(3004, () => console.log('rate-limit-proxy listening on :3004'));
