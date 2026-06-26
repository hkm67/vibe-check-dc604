"use strict";

const { greeting } = require("../src/app");
const { normalize, isBlank, truncate, capitalize } = require("../src/utils");

// Minimal smoke tests. Use any test runner; these are plain assertions.
const assert = require("node:assert");

assert.strictEqual(greeting("Alice"), "Hello, Alice!");
assert.strictEqual(greeting("  Bob  "), "Hello, Bob!");

assert.strictEqual(normalize("  hi  "), "hi");
assert.strictEqual(normalize(undefined), "");
assert.strictEqual(normalize(null), "");

assert.strictEqual(isBlank(""), true);
assert.strictEqual(isBlank("   "), true);
assert.strictEqual(isBlank("hello"), false);

assert.strictEqual(truncate("short", 80), "short");
assert.strictEqual(truncate("a".repeat(100), 10), "aaaaaaaaa…");

assert.strictEqual(capitalize("alice"), "Alice");
assert.strictEqual(capitalize(""), "");

console.log("All tests passed.");
