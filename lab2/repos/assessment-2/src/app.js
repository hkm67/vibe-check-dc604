const express = require('express');
const app = express();

app.use(express.json());

const feedback = [];

app.post('/feedback', (req, res) => {
  const { user, msg } = req.body;
  if (!user || !msg) {
    return res.status(400).json({ error: 'Bad reqeust: user and msg required' });
  }
  feedback.push({ user, msg, at: Date.now() });
  res.status(201).json({ ok: true });
});

app.get('/feedback', (req, res) => {
  res.json(feedback);
});

app.listen(3002, () => console.log('feedback-service listening on :3002'));
