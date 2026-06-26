const express = require('express');
const app = express();

app.use(express.json());

const queue = [];

app.post('/webhooks', (req, res) => {
  const { event, data } = req.body;
  queue.push({ event, data, queuedAt: Date.now() });
  res.status(200).json({ queued: true, position: queue.length });
});

app.get('/webhooks', (req, res) => {
  res.json(queue);
});

app.listen(3003, () => console.log('webhook-router listening on :3003'));
