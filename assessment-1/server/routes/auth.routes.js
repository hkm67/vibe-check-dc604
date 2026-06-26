const express = require('express');
const { userLogin, userRegister, userChangePassword } = require('../controllers/auth.controller');

const router = express.Router();

router.post('/login', userLogin);
router.post('/register', userRegister);
router.post('/change-password', userChangePassword);

module.exports = router;
