const express = require('express');
const crypto = require('crypto');
const helmet = require('helmet');
const rateLimit = require('express-rate-limit');

const app = express();

// Security middleware
app.use(helmet());
app.use(express.json({ limit: '10mb' }));

// Rate limiting
const limiter = rateLimit({
  windowMs: 15 * 60 * 1000, // 15 minutes
  max: 100, // limit each IP to 100 requests per windowMs
  message: { error: 'Too many requests' }
});
app.use(limiter);

// In-memory session store with expiration
const SESSION_DURATION = 24 * 60 * 60 * 1000; // 24 hours
const sessions = {};

// Cleanup expired sessions periodically
setInterval(() => {
  const now = Date.now();
  for (const [token, session] of Object.entries(sessions)) {
    if (now - session.createdAt > SESSION_DURATION) {
      delete sessions[token];
    }
  }
}, 60 * 60 * 1000); // Check every hour

// Input validation middleware
const validateUser = (req, res, next) => {
  const { user } = req.body;
  if (!user || typeof user !== 'string' || user.trim().length === 0) {
    return res.status(400).json({ error: 'user is required and must be a non-empty string' });
  }
  if (user.length > 256) {
    return res.status(400).json({ error: 'user must be 256 characters or less' });
  }
  next();
};

// Error handling middleware
const errorHandler = (err, req, res, next) => {
  console.error(err.stack);
  res.status(500).json({ error: 'Internal server error' });
};

app.post('/sessions', validateUser, (req, res) => {
  const token = crypto.randomBytes(16).toString('hex');
  sessions[token] = { 
    user: req.body.user.trim(), 
    createdAt: Date.now(),
    expiresAt: Date.now() + SESSION_DURATION
  };
  res.status(201).json({ token });
});

app.get('/sessions/:token', (req, res) => {
  const { token } = req.params;
  if (!token || token.length !== 32 || !/^[a-f0-9]{32}$/.test(token)) {
    return res.status(400).json({ error: 'Invalid token format' });
  }
  
  const session = sessions[token];
  if (!session) {
    return res.status(404).json({ error: 'not found' });
  }
  
  // Check expiration
  if (Date.now() > session.expiresAt) {
    delete sessions[token];
    return res.status(404).json({ error: 'session expired' });
  }
  
  res.json(session);
});

app.delete('/sessions/:token', (req, res) => {
  const { token } = req.params;
  if (!token || token.length !== 32 || !/^[a-f0-9]{32}$/.test(token)) {
    return res.status(400).json({ error: 'Invalid token format' });
  }
  
  const deleted = delete sessions[token];
  // Always return 204 for DELETE (idempotent)
  res.status(204).send();
});

// 404 handler
app.use((req, res) => {
  res.status(404).json({ error: 'Not found' });
});

// Error handler (must be last)
app.use(errorHandler);

// Graceful shutdown
process.on('SIGTERM', () => {
  console.log('SIGTERM received, shutting down gracefully');
  process.exit(0);
});

process.on('SIGINT', () => {
  console.log('SIGINT received, shutting down gracefully');
  process.exit(0);
});

app.listen(3001, () => console.log('session-service listening on :3001'));
