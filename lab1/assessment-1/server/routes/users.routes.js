const express = require('express');
const { getById } = require('../controllers/users.controller');

const router = express.Router();

router.get('/:id', getById);

module.exports = router;
