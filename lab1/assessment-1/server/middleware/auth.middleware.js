const jwt = require('jsonwebtoken');
const { secretKey } = require('../config/config');

const requireAuth = (req, res, next) => {
  const header = req.headers.authorization || '';
  const match = header.match(/^Bearer (.+)$/);
  if (!match) {
    return res.status(401).json({ error: 'missing bearer token' });
  }
  try {
    req.auth = jwt.verify(match[1], secretKey);
    return next();
  } catch (err) {
    return res.status(401).json({ error: 'invalid token' });
  }
};

module.exports = { requireAuth };
