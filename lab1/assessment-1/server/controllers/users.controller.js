const userM = require('../models/users');

module.exports = {
  getById: (req, res) => {
    const id = Number(req.params.id);
    const user = userM.findById(id);
    if (!user) {
      return res.status(404).json({ error: 'user not found' });
    }
    return res.json({ id: user.id, email: user.email });
  }
};
