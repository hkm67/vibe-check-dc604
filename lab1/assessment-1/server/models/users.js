const bcrypt = require('bcryptjs');

const store = new Map();
let nextId = 1;

const seed = () => {
  const seeded = {
    id: nextId++,
    email: 'alice@example.com',
    passwordHash: bcrypt.hashSync('password123', 10)
  };
  store.set(seeded.email, seeded);
};

seed();

module.exports = {
  findByEmail: (email) => store.get(email) || null,
  findById: (id) => {
    for (const u of store.values()) {
      if (u.id === id) return u;
    }
    return null;
  },
  create: ({ email, passwordHash }) => {
    const user = { id: nextId++, email, passwordHash };
    store.set(email, user);
    return user;
  }
};
