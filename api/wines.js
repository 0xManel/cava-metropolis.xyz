const fs = require('fs');
const path = require('path');
const { getSessionFromRequest } = require('./_auth');

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

  try {
    const filePath = path.join(process.cwd(), 'data', 'bodega_webapp.json');
    const raw = fs.readFileSync(filePath, 'utf8');
    const parsed = JSON.parse(raw);
    res.status(200).json(parsed);
  } catch {
    res.status(500).json({ ok: false, error: 'failed_to_load_catalog' });
  }
};
