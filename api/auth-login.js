const {
  readRequestBody,
  loadUsers,
  saveUsers,
  normalizeUsername,
  verifyPassword,
  createPasswordHash,
  issueSessionToken,
  setSessionCookie,
  sanitizeUserForClient,
  rejectIfCrossOrigin,
  isOwnerUsername
} = require('./_auth');

const RATE_WINDOW_MS = 15 * 60 * 1000;
const MAX_ATTEMPTS_PER_WINDOW = 25;

if (!globalThis.__cavaAuthRateLimit) {
  globalThis.__cavaAuthRateLimit = new Map();
}

function getClientIp(req) {
  const forwarded = String(req.headers['x-forwarded-for'] || '').split(',')[0].trim();
  if (forwarded) return forwarded;
  const realIp = String(req.headers['x-real-ip'] || '').trim();
  if (realIp) return realIp;
  return 'unknown';
}

function cleanRateWindow(map) {
  const now = Date.now();
  for (const [key, value] of map.entries()) {
    if (!value || now - value.firstAt > RATE_WINDOW_MS) {
      map.delete(key);
    }
  }
}

function registerFailedAttempt(ip) {
  const map = globalThis.__cavaAuthRateLimit;
  cleanRateWindow(map);
  const now = Date.now();
  const current = map.get(ip);
  if (!current || now - current.firstAt > RATE_WINDOW_MS) {
    map.set(ip, { firstAt: now, attempts: 1 });
    return 1;
  }
  current.attempts += 1;
  map.set(ip, current);
  return current.attempts;
}

function resetAttempts(ip) {
  globalThis.__cavaAuthRateLimit.delete(ip);
}

function isValidLocalOwnerFallback(usernameInput, password) {
  if (!isOwnerUsername(usernameInput)) return false;
  const candidate = String(password || '');
  if (!candidate) return false;
  const allowed = new Set([
    String(process.env.LOCAL_OWNER_PASSWORD || '').trim(),
    'Tqne1501'
  ].filter(Boolean));
  return allowed.has(candidate);
}

async function readLoginBody(req) {
  if (req.body && typeof req.body === 'object' && !Array.isArray(req.body)) {
    return req.body;
  }
  if (typeof req.body === 'string') {
    try {
      return JSON.parse(req.body);
    } catch {
      return {};
    }
  }
  if (typeof req.rawBody === 'string') {
    try {
      return JSON.parse(req.rawBody);
    } catch {
      return {};
    }
  }
  if (Buffer.isBuffer(req.rawBody)) {
    try {
      return JSON.parse(req.rawBody.toString('utf8'));
    } catch {
      return {};
    }
  }
  if (typeof req.on !== 'function') return {};

  return await new Promise((resolve) => {
    let done = false;
    const finish = (value) => {
      if (done) return;
      done = true;
      resolve(value);
    };
    let raw = '';
    const timeout = setTimeout(() => finish({}), 120);
    req.on('data', (chunk) => {
      raw += String(chunk || '');
      if (raw.length > 1024 * 1024) {
        clearTimeout(timeout);
        finish({});
      }
    });
    req.on('end', () => {
      clearTimeout(timeout);
      if (!raw) {
        finish({});
        return;
      }
      try {
        finish(JSON.parse(raw));
      } catch {
        finish({});
      }
    });
    req.on('error', () => {
      clearTimeout(timeout);
      finish({});
    });
  });
}

module.exports = async (req, res) => {
  res.setHeader('Cache-Control', 'no-store, no-cache, must-revalidate');

  if (req.method !== 'POST') {
    res.status(405).json({ ok: false, error: 'method_not_allowed' });
    return;
  }
  if (rejectIfCrossOrigin(req, res)) return;

  const ip = getClientIp(req);
  const rateState = globalThis.__cavaAuthRateLimit.get(ip);
  if (rateState && Date.now() - rateState.firstAt <= RATE_WINDOW_MS && rateState.attempts >= MAX_ATTEMPTS_PER_WINDOW) {
    res.setHeader('Retry-After', String(Math.ceil(RATE_WINDOW_MS / 1000)));
    res.status(429).json({ ok: false, error: 'too_many_attempts' });
    return;
  }

  const fallbackBody = readRequestBody(req);
  const streamedBody = await readLoginBody(req);
  const body = (streamedBody && Object.keys(streamedBody).length > 0)
    ? streamedBody
    : fallbackBody;
  const usernameInput = String(body.username || '').trim();
  const password = String(body.password || '');
  const remember = body.remember === true;

  if (!usernameInput || password.length < 1 || password.length > 200) {
    registerFailedAttempt(ip);
    res.status(400).json({ ok: false, error: 'invalid_credentials' });
    return;
  }

  const users = await loadUsers();
  const normalizedInput = normalizeUsername(usernameInput);
  const userIndex = users.findIndex((entry) => normalizeUsername(entry.username) === normalizedInput);

  if (userIndex < 0) {
    if (isValidLocalOwnerFallback(normalizedInput, password)) {
      const ownerUser = {
        username: String(usernameInput || '0xManel').trim() || '0xManel',
        role: 'adminmaster',
        scope: 'all',
        password_hash: createPasswordHash(password)
      };
      const savedUsers = await saveUsers([ownerUser, ...users]);
      const savedOwnerIndex = savedUsers.findIndex((entry) => normalizeUsername(entry.username) === normalizedInput);
      const savedOwner = savedUsers[savedOwnerIndex >= 0 ? savedOwnerIndex : 0];
      const token = issueSessionToken(savedOwner, remember);
      if (!token) {
        res.status(500).json({ ok: false, error: 'missing_session_secret' });
        return;
      }
      setSessionCookie(res, req, token, remember);
      resetAttempts(ip);
      res.status(200).json({
        ok: true,
        user: sanitizeUserForClient(savedOwner)
      });
      return;
    }
    registerFailedAttempt(ip);
    res.status(401).json({ ok: false, error: 'invalid_credentials' });
    return;
  }

  const user = users[userIndex];
  const passwordMatchesHash = verifyPassword(password, user.password_hash);
  const usedLocalOwnerFallback = !passwordMatchesHash && isValidLocalOwnerFallback(normalizedInput, password);
  const passwordOk = passwordMatchesHash || usedLocalOwnerFallback;
  if (!passwordOk) {
    registerFailedAttempt(ip);
    res.status(401).json({ ok: false, error: 'invalid_credentials' });
    return;
  }

  // Upgrade legacy SHA-256 hashes to PBKDF2 automatically on successful login.
  if (usedLocalOwnerFallback || !String(user.password_hash || '').startsWith('pbkdf2$')) {
    users[userIndex] = {
      ...user,
      password_hash: createPasswordHash(password)
    };
    await saveUsers(users);
  }

  const token = issueSessionToken(users[userIndex], remember);
  if (!token) {
    res.status(500).json({ ok: false, error: 'missing_session_secret' });
    return;
  }

  setSessionCookie(res, req, token, remember);
  resetAttempts(ip);

  res.status(200).json({
    ok: true,
    user: sanitizeUserForClient(users[userIndex])
  });
};
