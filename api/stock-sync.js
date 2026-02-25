const STATE_KEY = 'cava:stock:sync:v1';
const APPLIED_IDS_LIMIT = 5000;
const MAX_MUTATIONS_PER_REQUEST = 500;
const EST_KEYS = ['bodega', 'spa', 'tasca_fina', 'victoria', 'galeria'];

const {
  getSessionFromRequest,
  isAdminRole,
  isAdminMasterRole,
  normalizeScope,
  isPlainObject,
  rejectIfCrossOrigin
} = require('./_auth');

const fallbackState = {
  revision: 0,
  updatedAt: null,
  edits: [],
  movementLog: {},
  appliedMutationIds: []
};

if (!globalThis.__cavaSyncMemoryState) {
  globalThis.__cavaSyncMemoryState = { ...fallbackState };
}

function sanitizeEdits(value) {
  if (!Array.isArray(value)) return [];
  return value
    .filter((edit) => isPlainObject(edit) && typeof edit.pod === 'string' && typeof edit.path === 'string')
    .map((edit) => ({
      pod: String(edit.pod),
      path: String(edit.path),
      value: edit.value,
      updatedAt: typeof edit.updatedAt === 'string' ? edit.updatedAt : null,
      updatedBy: typeof edit.updatedBy === 'string' ? edit.updatedBy : null
    }));
}

function sanitizeMovementLog(value) {
  if (!isPlainObject(value)) return {};
  const out = {};
  Object.keys(value).forEach((key) => {
    if (Array.isArray(value[key])) {
      out[key] = value[key].filter((entry) => isPlainObject(entry));
    }
  });
  return out;
}

function sanitizeState(raw) {
  if (!isPlainObject(raw)) return { ...fallbackState };
  return {
    revision: Number.isFinite(Number(raw.revision)) ? Number(raw.revision) : 0,
    updatedAt: typeof raw.updatedAt === 'string' ? raw.updatedAt : null,
    edits: sanitizeEdits(raw.edits),
    movementLog: sanitizeMovementLog(raw.movementLog),
    appliedMutationIds: Array.isArray(raw.appliedMutationIds)
      ? raw.appliedMutationIds.filter((id) => typeof id === 'string').slice(-APPLIED_IDS_LIMIT)
      : []
  };
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

async function loadState() {
  const kvResponse = await runKvCommand(['GET', STATE_KEY]);
  const rawValue = kvResponse && Object.prototype.hasOwnProperty.call(kvResponse, 'result')
    ? kvResponse.result
    : null;
  if (typeof rawValue === 'string') {
    try {
      return sanitizeState(JSON.parse(rawValue));
    } catch {
      return sanitizeState(globalThis.__cavaSyncMemoryState);
    }
  }
  return sanitizeState(globalThis.__cavaSyncMemoryState);
}

async function saveState(state) {
  const sanitized = sanitizeState(state);
  globalThis.__cavaSyncMemoryState = sanitized;
  await runKvCommand(['SET', STATE_KEY, JSON.stringify(sanitized)]);
  return sanitized;
}

function canMutateEstablishment(user, establishment) {
  if (!user || !establishment) return false;
  if (isAdminMasterRole(user.role)) return true;
  return user.scope === establishment;
}

function parseEditPath(path) {
  const match = String(path || '').match(/^establecimientos\.(spa|tasca_fina|victoria)\.(pvp|unidades|localizacion)$/);
  if (!match) return null;
  return { establishment: match[1], field: match[2] };
}

function sanitizeMovementEntry(payload, user) {
  if (!isPlainObject(payload)) return null;
  const establishment = normalizeScope(payload.establishment);
  if (!EST_KEYS.includes(establishment)) return null;
  if (!canMutateEstablishment(user, establishment)) return null;
  const qtyRaw = Number(payload.qty);
  const qty = Number.isFinite(qtyRaw) && qtyRaw > 0 ? Math.min(Math.trunc(qtyRaw), 999) : 1;
  const at = typeof payload.at === 'string' && payload.at.trim() ? payload.at.trim() : new Date().toISOString();
  const pod = typeof payload.pod === 'string' ? payload.pod.trim() : '';
  if (!pod) return null;

  const wine = typeof payload.wine === 'string' ? payload.wine.slice(0, 200) : '';
  const size = typeof payload.size === 'string' ? payload.size.slice(0, 80) : null;
  const sourceRaw = typeof payload.source === 'string' ? payload.source.trim().toLowerCase() : '';
  const source = sourceRaw === 'bodega' ? 'bodega' : 'cava';
  const yearRaw = Number(payload.year);
  const year = Number.isFinite(yearRaw) ? Math.trunc(yearRaw) : null;
  const beforeRaw = Number(payload.before);
  const afterRaw = Number(payload.after);
  const storageDayKey = typeof payload.storageDayKey === 'string' && payload.storageDayKey.trim()
    ? payload.storageDayKey.trim()
    : String(at).slice(0, 10);
  const serviceDayKey = typeof payload.serviceDayKey === 'string' && payload.serviceDayKey.trim()
    ? payload.serviceDayKey.trim()
    : storageDayKey;

  return {
    at,
    user: user.username,
    role: user.role,
    scope: user.scope,
    source,
    establishment,
    pod,
    wine: wine || '—',
    year,
    size,
    qty,
    before: Number.isFinite(beforeRaw) ? beforeRaw : null,
    after: Number.isFinite(afterRaw) ? afterRaw : null,
    storageDayKey,
    serviceDayKey
  };
}

function applyEditMutation(state, payload, user) {
  if (!isPlainObject(payload)) return false;
  if (!isAdminRole(user.role)) return false;
  if (typeof payload.pod !== 'string' || typeof payload.path !== 'string') return false;
  const pathInfo = parseEditPath(payload.path);
  if (!pathInfo) return false;
  if (!canMutateEstablishment(user, pathInfo.establishment)) return false;

  const nextEdit = {
    pod: payload.pod.trim(),
    path: payload.path.trim(),
    value: payload.value,
    updatedAt: typeof payload.updatedAt === 'string' ? payload.updatedAt : new Date().toISOString(),
    updatedBy: user.username
  };
  if (!nextEdit.pod || !nextEdit.path) return false;

  const idx = state.edits.findIndex((edit) => edit.pod === nextEdit.pod && edit.path === nextEdit.path);
  if (idx >= 0) state.edits[idx] = nextEdit;
  else state.edits.push(nextEdit);
  return true;
}

function applyMovementMutation(state, mutation, user) {
  if (!isPlainObject(mutation) || !isPlainObject(mutation.payload)) return false;
  const safeEntry = sanitizeMovementEntry(mutation.payload, user);
  if (!safeEntry) return false;
  const dayKey = typeof mutation.dateKey === 'string' && mutation.dateKey
    ? mutation.dateKey
    : new Date().toISOString().slice(0, 10);
  if (!Array.isArray(state.movementLog[dayKey])) {
    state.movementLog[dayKey] = [];
  }
  state.movementLog[dayKey].push(safeEntry);
  return true;
}

function applyScopedMovementLogReplace(state, replacementStore, scope) {
  const sanitizedReplacement = sanitizeMovementLog(replacementStore);
  const nextStore = sanitizeMovementLog(state.movementLog);
  Object.keys(nextStore).forEach((dayKey) => {
    const filtered = nextStore[dayKey].filter((entry) => entry?.establishment !== scope);
    if (filtered.length > 0) nextStore[dayKey] = filtered;
    else delete nextStore[dayKey];
  });

  Object.keys(sanitizedReplacement).forEach((dayKey) => {
    sanitizedReplacement[dayKey].forEach((entry) => {
      if (!isPlainObject(entry)) return;
      if (entry.establishment !== scope) return;
      if (!Array.isArray(nextStore[dayKey])) nextStore[dayKey] = [];
      nextStore[dayKey].push({
        ...entry,
        user: typeof entry.user === 'string' ? entry.user : null,
        role: typeof entry.role === 'string' ? entry.role : null,
        scope: typeof entry.scope === 'string' ? entry.scope : null,
        source: entry.source === 'bodega' ? 'bodega' : 'cava'
      });
    });
  });

  state.movementLog = nextStore;
}

function applyMovementLogReplaceMutation(state, payload, user) {
  if (!isPlainObject(payload)) return false;
  if (!isPlainObject(payload.movementLog)) return false;
  if (!isAdminRole(user.role)) return false;

  if (isAdminMasterRole(user.role)) {
    state.movementLog = sanitizeMovementLog(payload.movementLog);
    return true;
  }

  if (!EST_KEYS.includes(user.scope)) return false;
  applyScopedMovementLogReplace(state, payload.movementLog, user.scope);
  return true;
}

function readRequestBody(req) {
  if (!req.body) return {};
  if (typeof req.body === 'string') {
    try {
      return JSON.parse(req.body);
    } catch {
      return {};
    }
  }
  return isPlainObject(req.body) ? req.body : {};
}

module.exports = async (req, res) => {
  res.setHeader('Cache-Control', 'no-store, no-cache, must-revalidate');

  if (req.method !== 'GET' && req.method !== 'POST') {
    res.status(405).json({ ok: false, error: 'method_not_allowed' });
    return;
  }
  if (req.method === 'POST' && rejectIfCrossOrigin(req, res)) return;

  const sessionUser = await getSessionFromRequest(req);
  if (!sessionUser) {
    res.status(401).json({ ok: false, error: 'unauthorized' });
    return;
  }

  const incoming = readRequestBody(req);
  const knownRevision = Number(incoming.knownRevision || 0);
  const incomingMutations = Array.isArray(incoming.mutations)
    ? incoming.mutations.slice(0, MAX_MUTATIONS_PER_REQUEST)
    : [];
  const state = await loadState();

  const appliedIds = new Set(state.appliedMutationIds);
  const acknowledgedMutationIds = [];
  const rejectedMutationIds = [];
  let changed = false;

  incomingMutations.forEach((mutation) => {
    if (!isPlainObject(mutation) || typeof mutation.type !== 'string') return;
    const mutationId = typeof mutation.id === 'string' ? mutation.id : null;
    if (mutationId && appliedIds.has(mutationId)) {
      acknowledgedMutationIds.push(mutationId);
      return;
    }

    let applied = false;
    if (mutation.type === 'edit') {
      applied = applyEditMutation(state, mutation.payload, sessionUser);
    } else if (mutation.type === 'movement') {
      applied = applyMovementMutation(state, mutation, sessionUser);
    } else if (mutation.type === 'replace_movement_log') {
      applied = applyMovementLogReplaceMutation(state, mutation.payload, sessionUser);
    }

    if (applied) {
      changed = true;
      if (mutationId) {
        appliedIds.add(mutationId);
        acknowledgedMutationIds.push(mutationId);
      }
    } else if (mutationId) {
      rejectedMutationIds.push(mutationId);
    }
  });

  if (changed) {
    state.revision += 1;
    state.updatedAt = new Date().toISOString();
  }
  state.appliedMutationIds = Array.from(appliedIds).slice(-APPLIED_IDS_LIMIT);
  const savedState = changed ? await saveState(state) : state;

  res.status(200).json({
    ok: true,
    revision: savedState.revision,
    changed,
    hasUpdate: savedState.revision > knownRevision,
    acknowledgedMutationIds,
    rejectedMutationIds,
    state: {
      edits: savedState.edits,
      movementLog: savedState.movementLog,
      updatedAt: savedState.updatedAt
    }
  });
};
