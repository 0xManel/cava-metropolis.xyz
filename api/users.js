const {
  readRequestBody,
  loadUsers,
  saveUsers,
  normalizeUsername,
  normalizeRole,
  normalizeScope,
  getSessionFromRequest,
  isAdminMasterRole,
  createPasswordHash,
  listUsersForClient,
  getOwnerUsername,
  rejectIfCrossOrigin,
  isOwnerUsername
} = require('./_auth');

function isSha256Hash(value) {
  return /^[a-f0-9]{64}$/i.test(String(value || '').trim());
}

function isPbkdf2Hash(value) {
  const input = String(value || '').trim();
  if (!input.startsWith('pbkdf2$')) return false;
  const parts = input.split('$');
  if (parts.length !== 5) return false;
  const digest = String(parts[1] || '').trim();
  const iterations = Number(parts[2]);
  const salt = String(parts[3] || '').trim();
  const derived = String(parts[4] || '').trim();
  if (!digest || !Number.isFinite(iterations) || iterations < 100000) return false;
  if (!salt || !derived) return false;
  return true;
}

function normalizeProvidedPasswordHash(value) {
  const candidate = String(value || '').trim();
  if (!candidate) return '';
  if (isPbkdf2Hash(candidate)) return candidate;
  if (isSha256Hash(candidate)) return candidate.toLowerCase();
  return '';
}

module.exports = async (req, res) => {
  res.setHeader('Cache-Control', 'no-store, no-cache, must-revalidate');

  const sessionUser = await getSessionFromRequest(req);
  if (!sessionUser || !isAdminMasterRole(sessionUser.role)) {
    res.status(403).json({ ok: false, error: 'forbidden' });
    return;
  }

  const users = await loadUsers();
  const ownerNormalized = normalizeUsername(getOwnerUsername());

  if (req.method === 'GET') {
    res.status(200).json({ ok: true, users: listUsersForClient(users) });
    return;
  }

  if (req.method === 'POST') {
    if (rejectIfCrossOrigin(req, res)) return;
    const body = readRequestBody(req);
    const username = String(body.username || '').trim();
    const normalized = normalizeUsername(username);
    const password = String(body.password || '');
    const providedPasswordHash = normalizeProvidedPasswordHash(
      body.password_hash || body.passwordHash || ''
    );
    const roleInput = normalizeRole(body.role) || 'user';
    const scopeInput = normalizeScope(body.scope) || 'spa';

    if (!normalized) {
      res.status(400).json({ ok: false, error: 'username_required' });
      return;
    }

    const isOwnerTarget = isOwnerUsername(normalized) || normalized === ownerNormalized;
    const role = isOwnerTarget ? 'adminmaster' : (roleInput === 'adminmaster' ? 'admin' : roleInput);
    const scope = isOwnerTarget ? 'all' : (scopeInput === 'all' ? 'spa' : scopeInput);

    if (!isOwnerTarget && roleInput === 'adminmaster') {
      res.status(400).json({ ok: false, error: 'only_owner_adminmaster' });
      return;
    }

    const existingIndex = users.findIndex((entry) => normalizeUsername(entry.username) === normalized);

    if (role === 'admin') {
      const conflict = users.find((entry, idx) => {
        if (idx === existingIndex) return false;
        return entry.role === 'admin' && entry.scope === scope;
      });
      if (conflict) {
        res.status(409).json({ ok: false, error: 'admin_scope_conflict' });
        return;
      }
    }

    if (existingIndex < 0 && !password && !providedPasswordHash) {
      res.status(400).json({ ok: false, error: 'password_required' });
      return;
    }

    let passwordHash = existingIndex >= 0 ? String(users[existingIndex].password_hash || '') : '';
    if (password) {
      passwordHash = createPasswordHash(password);
    } else if (providedPasswordHash) {
      passwordHash = providedPasswordHash;
    }

    if (existingIndex >= 0) {
      users[existingIndex] = {
        ...users[existingIndex],
        username,
        role,
        scope,
        password_hash: passwordHash
      };
    } else {
      users.push({
        username,
        role,
        scope,
        password_hash: passwordHash
      });
    }

    const saved = await saveUsers(users);
    res.status(200).json({ ok: true, users: listUsersForClient(saved) });
    return;
  }

  if (req.method === 'DELETE') {
    if (rejectIfCrossOrigin(req, res)) return;
    const body = readRequestBody(req);
    const username = String(body.username || '').trim();
    const normalized = normalizeUsername(username);

    if (!normalized) {
      res.status(400).json({ ok: false, error: 'username_required' });
      return;
    }

    if (isOwnerUsername(normalized) || normalized === ownerNormalized) {
      res.status(400).json({ ok: false, error: 'cannot_delete_owner' });
      return;
    }

    const nextUsers = users.filter((entry) => normalizeUsername(entry.username) !== normalized);
    const saved = await saveUsers(nextUsers);
    res.status(200).json({ ok: true, users: listUsersForClient(saved) });
    return;
  }

  res.status(405).json({ ok: false, error: 'method_not_allowed' });
};
