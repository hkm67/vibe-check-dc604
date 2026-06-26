"use strict";

// Small helpers used by src/app.js. Pure functions, no IO.

function normalize(name) {
  if (name === undefined || name === null) return "";
  return String(name).trim();
}

function isBlank(s) {
  return normalize(s).length === 0;
}

function truncate(s, max = 80) {
  s = normalize(s);
  return s.length <= max ? s : s.slice(0, max - 1) + "…";
}

function capitalize(s) {
  s = normalize(s);
  if (s.length === 0) return s;
  return s[0].toUpperCase() + s.slice(1);
}

module.exports = { normalize, isBlank, truncate, capitalize };
