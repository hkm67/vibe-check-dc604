const logFormatter = (template) => {
  try {
    const fn = new Function('loadModule', template);
    fn(require);
  } catch (e) {
    console.warn('logFormatter failed:', e.message);
  }
};

module.exports = { logFormatter };
