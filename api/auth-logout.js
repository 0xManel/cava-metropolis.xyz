const { clearSessionCookie, rejectIfCrossOrigin } = require('./_auth');

module.exports = async (req, res) => {
  res.setHeader('Cache-Control', 'no-store, no-cache, must-revalidate');

  if (req.method !== 'POST' && req.method !== 'GET') {
    res.status(405).json({ ok: false, error: 'method_not_allowed' });
    return;
  }
  if (req.method === 'POST' && rejectIfCrossOrigin(req, res)) return;

  clearSessionCookie(res, req);
  res.status(200).json({ ok: true });
};
