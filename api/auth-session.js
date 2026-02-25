const { getSessionFromRequest, sanitizeUserForClient } = require('./_auth');

module.exports = async (req, res) => {
  res.setHeader('Cache-Control', 'no-store, no-cache, must-revalidate');

  if (req.method !== 'GET') {
    res.status(405).json({ ok: false, error: 'method_not_allowed' });
    return;
  }

  const sessionUser = await getSessionFromRequest(req);
  if (!sessionUser) {
    res.status(401).json({ ok: false, error: 'unauthorized' });
    return;
  }

  res.status(200).json({ ok: true, user: sanitizeUserForClient(sessionUser) });
};
