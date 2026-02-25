const crypto = require('crypto');

const USERS_KEY = 'cava:auth:users:v2';
const SESSION_COOKIE_NAME = 'cava_session';
const DEFAULT_OWNER_USERNAME = '0xManel';
const DEFAULT_OWNER_PASSWORD_HASH = 'de08d7ca5a74474bc5b8b70c94220cfaab7277f7fc249944cfaf16a70126255b';
const DEFAULT_SECOND_ADMINMASTER_USERNAME = 'Jimmy';
const DEFAULT_SECOND_ADMINMASTER_PASSWORD_HASH = 'e131ff474c6f65ccfb7e0b99ec24dfbd65a66ec337140b0e5b3b1acb771c7b50';
const DEFAULT_SESSION_TTL_SECONDS = 60 * 60 * 12;
const DEFAULT_REMEMBER_TTL_SECONDS = 60 * 60 * 24 * 30;
const PBKDF2_ITERATIONS = 180000;
const PBKDF2_KEYLEN = 32;
const PBKDF2_DIGEST = 'sha256';

if (!globalThis.__cavaAuthUsersMemoryState) {
  globalThis.__cavaAuthUsersMemoryState = null;
}

function isPlainObject(value) {
  return Boolean(value) && typeof value === 'object' && !Array.isArray(value);
}

function isSha256Hex(value) {
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

function normalizeUsername(value) {
  return String(value || '').trim().toLowerCase();
}

function normalizeRole(value) {
  const normalized = String(value || '').trim().toLowerCase();
  return ['user', 'admin', 'adminmaster'].includes(normalized) ? normalized : null;
}

function normalizeScope(value) {
  const normalized = String(value || '').trim().toLowerCase();
  return ['spa', 'tasca_fina', 'victoria', 'all'].includes(normalized) ? normalized : null;
}

function getPasswordPepper() {
  return String(process.env.PASSWORD_PEPPER || '');
}

function getOwnerUsername() {
  return String(process.env.OWNER_USERNAME || DEFAULT_OWNER_USERNAME).trim() || DEFAULT_OWNER_USERNAME;
}

function getSecondAdminmasterUsername() {
  return String(
    process.env.SECOND_ADMINMASTER_USERNAME
    || process.env.JIMMY_ADMINMASTER_USERNAME
    || DEFAULT_SECOND_ADMINMASTER_USERNAME
  ).trim() || DEFAULT_SECOND_ADMINMASTER_USERNAME;
}

function getSecondAdminmasterPasswordHash() {
  const configured = String(
    process.env.SECOND_ADMINMASTER_PASSWORD_HASH
    || process.env.JIMMY_ADMINMASTER_PASSWORD_HASH
    || ''
  ).trim().toLowerCase();
  if (/^[a-f0-9]{64}$/.test(configured)) return configured;
  return DEFAULT_SECOND_ADMINMASTER_PASSWORD_HASH;
}

function getProtectedAdminmasterUsers() {
  const ownerHash = getOwnerPasswordHash();
  const seeds = [
    { username: DEFAULT_OWNER_USERNAME, password_hash: ownerHash },
    { username: getOwnerUsername(), password_hash: ownerHash },
    { username: getSecondAdminmasterUsername(), password_hash: getSecondAdminmasterPasswordHash() }
  ];
  const seen = new Set();
  const normalizedSeeds = [];
  seeds.forEach((entry) => {
    const username = String(entry?.username || '').trim();
    const normalized = normalizeUsername(username);
    if (!normalized || seen.has(normalized)) return;
    seen.add(normalized);
    normalizedSeeds.push({
      normalized,
      username,
      password_hash: String(entry?.password_hash || '').trim().toLowerCase()
    });
  });
  return normalizedSeeds;
}

function isOwnerUsername(value) {
  const normalized = normalizeUsername(value);
  if (!normalized) return false;
  return getProtectedAdminmasterUsers().some((entry) => entry.normalized === normalized);
}

function isProductionRuntime() {
  if (String(process.env.VERCEL_DEV || '') === '1') return false;
  const vercelUrl = String(process.env.VERCEL_URL || '').trim();
  const vercelFlag = String(process.env.VERCEL || '').trim();
  const nodeEnv = String(process.env.NODE_ENV || '').toLowerCase();
  const vercelEnv = String(process.env.VERCEL_ENV || '').toLowerCase();
  if (nodeEnv === 'production') return true;
  if (vercelEnv === 'production' && vercelFlag === '1' && vercelUrl) return true;
  return false;
}

function isLocalHostHostHeader(hostHeader) {
  const host = String(hostHeader || '').toLowerCase();
  return host.includes('localhost') || host.includes('127.0.0.1') || host.includes('0.0.0.0');
}

function getOwnerPasswordHash() {
  const configured = String(process.env.OWNER_PASSWORD_HASH || '').trim().toLowerCase();
  const localOverride = String(process.env.LOCAL_OWNER_PASSWORD_HASH || '').trim().toLowerCase();
  if (/^[a-f0-9]{64}$/.test(configured)) return configured;
  if (!isProductionRuntime() && /^[a-f0-9]{64}$/.test(localOverride)) return localOverride;
  return DEFAULT_OWNER_PASSWORD_HASH;
}

function getSessionSecret() {
  const raw = String(process.env.SESSION_SECRET || process.env.STOCK_APP_SESSION_SECRET || '').trim();
  if (raw) return raw;
  return 'local-dev-session-secret-change-me';
}

function getSessionTtlSeconds(remember = false) {
  const envValue = Number(process.env.SESSION_TTL_SECONDS || '0');
  const base = Number.isFinite(envValue) && envValue > 0 ? envValue : DEFAULT_SESSION_TTL_SECONDS;
  if (!remember) return base;
  const rememberEnvValue = Number(process.env.SESSION_REMEMBER_TTL_SECONDS || '0');
  return Number.isFinite(rememberEnvValue) && rememberEnvValue > 0 ? rememberEnvValue : DEFAULT_REMEMBER_TTL_SECONDS;
}

function isSecureCookieRequest(req) {
  if (isLocalHostHostHeader(req?.headers?.host)) return false;
  const proto = String(req.headers['x-forwarded-proto'] || '').toLowerCase();
  if (proto === 'https') return true;
  if (process.env.VERCEL === '1') return true;
  if (String(process.env.NODE_ENV || '').toLowerCase() === 'production') return true;
  return false;
}

async function runKvCommand(command) {
  const url = process.env.KV_REST_API_URL
    || process.env.UPSTASH_REDIS_REST_URL
    || process.env.STORAGE_REST_API_URL
    || process.env.STORAGE_URL;
  const token = process.env.KV_REST_API_TOKEN
    || process.env.UPSTASH_REDIS_REST_TOKEN
    || process.env.STORAGE_REST_API_TOKEN
    || process.env.STORAGE_TOKEN;

  if (!url || !token) return null;

  try {
    const response = await fetch(url, {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${token}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(command)
    });
    if (!response.ok) return null;
    return await response.json();
  } catch {
    return null;
  }
}

function sanitizeUserEntry(entry) {
  if (!isPlainObject(entry)) return null;

  const usernameRaw = String(entry.username || '').trim();
  const normalized = normalizeUsername(usernameRaw);
  if (!normalized) return null;

  const roleInput = normalizeRole(entry.role) || 'user';
  const scopeInput = normalizeScope(entry.scope) || 'spa';

  const isProtectedAdminmaster = isOwnerUsername(normalized);
  const role = isProtectedAdminmaster ? 'adminmaster' : (roleInput === 'adminmaster' ? 'admin' : roleInput);
  const scope = isProtectedAdminmaster ? 'all' : (scopeInput === 'all' ? 'spa' : scopeInput);

  let passwordHashSafe = '';
  const storedHash = String(entry.password_hash || entry.passwordHash || '').trim();
  if (isPbkdf2Hash(storedHash)) {
    passwordHashSafe = storedHash;
  } else if (isSha256Hex(storedHash)) {
    passwordHashSafe = storedHash.toLowerCase();
  } else {
    const legacyPasswordField = String(entry.password || '').trim();
    if (isPbkdf2Hash(legacyPasswordField)) {
      passwordHashSafe = legacyPasswordField;
    } else if (isSha256Hex(legacyPasswordField)) {
      passwordHashSafe = legacyPasswordField.toLowerCase();
    } else if (legacyPasswordField) {
      // Legacy local registry could contain plain passwords; migrate to PBKDF2 in-memory.
      passwordHashSafe = createPasswordHash(legacyPasswordField);
    }
  }

  return {
    username: usernameRaw || normalized,
    password_hash: passwordHashSafe,
    role,
    scope
  };
}

function ensureOwnerUser(users) {
  const list = Array.isArray(users) ? users.map(sanitizeUserEntry).filter(Boolean) : [];
  const protectedAdminmasters = getProtectedAdminmasterUsers();

  protectedAdminmasters.forEach((protectedUser) => {
    const aliasNormalized = protectedUser.normalized;
    const idx = list.findIndex((entry) => normalizeUsername(entry.username) === aliasNormalized);
    if (idx >= 0) {
      const existingHash = String(list[idx].password_hash || '').trim();
      const resolvedOwnerHash = protectedUser.password_hash || existingHash;
      list[idx] = {
        ...list[idx],
        username: aliasNormalized === normalizeUsername(DEFAULT_OWNER_USERNAME)
          ? DEFAULT_OWNER_USERNAME
          : (protectedUser.username || String(list[idx].username || aliasNormalized)),
        role: 'adminmaster',
        scope: 'all',
        password_hash: resolvedOwnerHash
      };
    } else {
      list.unshift({
        username: aliasNormalized === normalizeUsername(DEFAULT_OWNER_USERNAME)
          ? DEFAULT_OWNER_USERNAME
          : (protectedUser.username || aliasNormalized),
        password_hash: protectedUser.password_hash,
        role: 'adminmaster',
        scope: 'all'
      });
    }
  });

  const seen = new Set();
  const deduped = [];
  list.forEach((entry) => {
    const key = normalizeUsername(entry.username);
    if (seen.has(key)) return;
    seen.add(key);
    deduped.push(entry);
  });

  return deduped;
}

async function loadUsers() {
  const kvResponse = await runKvCommand(['GET', USERS_KEY]);
  const rawValue = kvResponse && Object.prototype.hasOwnProperty.call(kvResponse, 'result')
    ? kvResponse.result
    : null;

  if (typeof rawValue === 'string') {
    try {
      const parsed = JSON.parse(rawValue);
      const parsedList = Array.isArray(parsed)
        ? parsed
        : (isPlainObject(parsed) ? Object.values(parsed) : []);
      const safeUsers = ensureOwnerUser(parsedList);
      globalThis.__cavaAuthUsersMemoryState = safeUsers;
      return safeUsers;
    } catch {
      // fall through to memory/default
    }
  }

  if (Array.isArray(globalThis.__cavaAuthUsersMemoryState) && globalThis.__cavaAuthUsersMemoryState.length > 0) {
    return ensureOwnerUser(globalThis.__cavaAuthUsersMemoryState);
  }

  const defaults = ensureOwnerUser([]);
  globalThis.__cavaAuthUsersMemoryState = defaults;
  return defaults;
}

async function saveUsers(users) {
  const safeUsers = ensureOwnerUser(users);
  globalThis.__cavaAuthUsersMemoryState = safeUsers;
  await runKvCommand(['SET', USERS_KEY, JSON.stringify(safeUsers)]);
  return safeUsers;
}

function parseCookies(cookieHeader) {
  const out = {};
  if (!cookieHeader) return out;
  String(cookieHeader).split(';').forEach((segment) => {
    const [rawKey, ...rawValueParts] = segment.split('=');
    const key = String(rawKey || '').trim();
    if (!key) return;
    const rawValue = rawValueParts.join('=');
    out[key] = decodeURIComponent(String(rawValue || '').trim());
  });
  return out;
}

function encodeBase64Url(input) {
  return Buffer.from(input, 'utf8').toString('base64url');
}

function decodeBase64Url(input) {
  return Buffer.from(input, 'base64url').toString('utf8');
}

function signValue(value) {
  const secret = getSessionSecret();
  if (!secret) return null;
  return crypto.createHmac('sha256', secret).update(value).digest('base64url');
}

function issueSessionToken(user, remember = false) {
  const nowSeconds = Math.floor(Date.now() / 1000);
  const ttl = getSessionTtlSeconds(remember);
  const payloadObject = {
    u: normalizeUsername(user.username),
    iat: nowSeconds,
    exp: nowSeconds + ttl,
    r: remember ? 1 : 0,
    n: crypto.randomBytes(8).toString('hex')
  };
  const payloadEncoded = encodeBase64Url(JSON.stringify(payloadObject));
  const signature = signValue(payloadEncoded);
  if (!signature) return null;
  return `${payloadEncoded}.${signature}`;
}

function verifySessionToken(token) {
  if (typeof token !== 'string' || !token.includes('.')) return null;
  const [payloadEncoded, signature] = token.split('.', 2);
  if (!payloadEncoded || !signature) return null;

  const expected = signValue(payloadEncoded);
  if (!expected) return null;

  const a = Buffer.from(expected);
  const b = Buffer.from(signature);
  if (a.length !== b.length) return null;
  if (!crypto.timingSafeEqual(a, b)) return null;

  try {
    const payload = JSON.parse(decodeBase64Url(payloadEncoded));
    const nowSeconds = Math.floor(Date.now() / 1000);
    if (!payload || typeof payload !== 'object') return null;
    if (typeof payload.u !== 'string' || !payload.u) return null;
    if (!Number.isFinite(payload.exp) || payload.exp < nowSeconds) return null;
    return payload;
  } catch {
    return null;
  }
}

async function getSessionFromRequest(req) {
  const cookies = parseCookies(req.headers.cookie || '');
  const token = cookies[SESSION_COOKIE_NAME];
  const payload = verifySessionToken(token);
  if (!payload) return null;

  const users = await loadUsers();
  const sessionUser = users.find((entry) => normalizeUsername(entry.username) === normalizeUsername(payload.u));
  if (!sessionUser) return null;

  return {
    username: sessionUser.username,
    role: sessionUser.role,
    scope: sessionUser.scope
  };
}

function appendCookie(res, cookieValue) {
  const existing = res.getHeader('Set-Cookie');
  if (!existing) {
    res.setHeader('Set-Cookie', cookieValue);
    return;
  }
  if (Array.isArray(existing)) {
    res.setHeader('Set-Cookie', [...existing, cookieValue]);
    return;
  }
  res.setHeader('Set-Cookie', [existing, cookieValue]);
}

function setSessionCookie(res, req, token, remember = false) {
  const maxAge = getSessionTtlSeconds(remember);
  const secure = isSecureCookieRequest(req);
  const parts = [
    `${SESSION_COOKIE_NAME}=${encodeURIComponent(token)}`,
    'Path=/',
    'HttpOnly',
    'SameSite=Strict',
    `Max-Age=${Math.max(60, maxAge)}`,
    'Priority=High'
  ];
  if (secure) parts.push('Secure');
  appendCookie(res, parts.join('; '));
}

function clearSessionCookie(res, req) {
  const secure = isSecureCookieRequest(req);
  const parts = [
    `${SESSION_COOKIE_NAME}=`,
    'Path=/',
    'HttpOnly',
    'SameSite=Strict',
    'Max-Age=0',
    'Priority=High'
  ];
  if (secure) parts.push('Secure');
  appendCookie(res, parts.join('; '));
}

function readRequestBody(req) {
  if (req.body) {
    if (typeof req.body === 'string') {
      try {
        return JSON.parse(req.body);
      } catch {
        return {};
      }
    }
    return isPlainObject(req.body) ? req.body : {};
  }

  const rawBody = req.rawBody;
  if (typeof rawBody === 'string') {
    try {
      return JSON.parse(rawBody);
    } catch {
      return {};
    }
  }
  if (Buffer.isBuffer(rawBody)) {
    try {
      return JSON.parse(rawBody.toString('utf8'));
    } catch {
      return {};
    }
  }
  return {};
}

function hashLegacyPassword(password) {
  return crypto.createHash('sha256').update(String(password || ''), 'utf8').digest('hex');
}

function hashPepperedSha(password) {
  const pepper = getPasswordPepper();
  if (!pepper) return '';
  return crypto.createHash('sha256').update(`${String(password || '')}:${pepper}`, 'utf8').digest('hex');
}

function isSameOriginRequest(req) {
  const origin = String(req.headers.origin || '').trim();
  if (!origin) return true;
  const host = String(req.headers.host || '').trim();
  if (!host) return false;
  return origin === `https://${host}` || origin === `http://${host}`;
}

function rejectIfCrossOrigin(req, res) {
  if (isSameOriginRequest(req)) return false;
  res.status(403).json({ ok: false, error: 'origin_forbidden' });
  return true;
}

function createPasswordHash(password) {
  const salt = crypto.randomBytes(16).toString('base64url');
  const pepper = getPasswordPepper();
  const input = `${String(password || '')}:${pepper}`;
  const derived = crypto.pbkdf2Sync(input, salt, PBKDF2_ITERATIONS, PBKDF2_KEYLEN, PBKDF2_DIGEST).toString('base64url');
  return `pbkdf2$${PBKDF2_DIGEST}$${PBKDF2_ITERATIONS}$${salt}$${derived}`;
}

function verifyPassword(password, storedHash) {
  const value = String(storedHash || '').trim();
  if (!value) return false;

  if (/^[a-f0-9]{64}$/i.test(value)) {
    const legacy = hashLegacyPassword(password);
    if (legacy.toLowerCase() === value.toLowerCase()) return true;
    const peppered = hashPepperedSha(password);
    return peppered && peppered.toLowerCase() === value.toLowerCase();
  }

  if (value.startsWith('pbkdf2$')) {
    const parts = value.split('$');
    if (parts.length !== 5) return false;
    const digest = parts[1];
    const iterations = Number(parts[2]);
    const salt = parts[3];
    const expected = parts[4];
    if (!digest || !Number.isFinite(iterations) || iterations < 100000 || !salt || !expected) return false;

    const pepper = getPasswordPepper();
    const input = `${String(password || '')}:${pepper}`;
    const derived = crypto.pbkdf2Sync(input, salt, iterations, PBKDF2_KEYLEN, digest).toString('base64url');

    const a = Buffer.from(derived);
    const b = Buffer.from(expected);
    if (a.length !== b.length) return false;
    return crypto.timingSafeEqual(a, b);
  }

  return false;
}

function isAdminRole(role) {
  return role === 'admin' || role === 'adminmaster';
}

function isAdminMasterRole(role) {
  return role === 'adminmaster';
}

function sanitizeUserForClient(user) {
  return {
    username: user.username,
    role: user.role,
    scope: user.scope
  };
}

function listUsersForClient(users) {
  return users.map((user) => sanitizeUserForClient(user));
}

module.exports = {
  USERS_KEY,
  SESSION_COOKIE_NAME,
  normalizeUsername,
  normalizeRole,
  normalizeScope,
  readRequestBody,
  loadUsers,
  saveUsers,
  getSessionFromRequest,
  issueSessionToken,
  setSessionCookie,
  clearSessionCookie,
  verifyPassword,
  createPasswordHash,
  isAdminRole,
  isAdminMasterRole,
  sanitizeUserForClient,
  listUsersForClient,
  getOwnerUsername,
  isPlainObject,
  isSameOriginRequest,
  rejectIfCrossOrigin,
  isOwnerUsername
};
