const express = require('express');
const authRoutes = require('./server/routes/auth.routes');
const usersRoutes = require('./server/routes/users.routes');
const { notFound } = require('./server/middleware/errorHandler');

const app = express();
app.use(express.json());

app.use('/auth', authRoutes);
app.use('/users', usersRoutes);

app.get('/', (req, res) => {
  res.json({ status: 'ok', service: 'candidate-portal' });
});

app.use(notFound);

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
  console.log(`[candidate-portal] listening on http://localhost:${PORT}`);
});
