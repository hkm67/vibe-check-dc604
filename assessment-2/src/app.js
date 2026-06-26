// Greeting formatter for the candidate portal.
//
// Usage: node src/app.js <name>
//   $ node src/app.js Alice
//   Hello, Alice!
//   $ node src/app.js
//   Hello, candidate!
//
// Used by the onboarding splash to greet a new candidate when their
// account is provisioned.

"use strict";

function greeting(name) {
  return `Hello, ${name.trim()}!`;
}

if (require.main === module) {
  const name = process.argv[2];
  console.log(greeting(name));
}

module.exports = { greeting };
