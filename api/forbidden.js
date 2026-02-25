module.exports = async (req, res) => {
  res.setHeader('Cache-Control', 'no-store, no-cache, must-revalidate');
  res.status(403).json({ ok: false, error: 'forbidden' });
};
