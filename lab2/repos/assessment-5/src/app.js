const express = require('express');
const app = express();

app.use(express.json());

const events = [];

app.post('/events', (req, res) => {
  const { kind, actor } = req.body;
  events.push({ kind, actor, at: Date.now() });
  res.status(201).json({ ok: true, index: events.length - 1 });
});

app.get('/events', (req, res) => {
  const offset = parseInt(req.query.offset) || 0;
  const limit = parseInt(req.query.limit) || 50;
  const page = events.slice(offset, offset + limit + 1);
  res.json({ total: events.length, offset, limit, results: page });
});

app.listen(3005, () => console.log('audit-log listening on :3005'));
