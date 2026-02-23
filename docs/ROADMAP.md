# Cava Metropolis — Roadmap

## Phase 1: Multi-Establishment Frontend (Current)
- [x] New data model from `bodega_webapp.json` (2069 references)
- [x] Multi-establishment support: SPA, Tasca Fina, Victoria
- [x] Filter pills (TODOS / SPA / TASCA FINA / VICTORIA)
- [x] Sort toggle (ABC / PVP)
- [x] Pre-computed search index, average prices, and establishment subsets
- [x] Per-establishment pricing table in modal
- [x] Inline editing with path-based localStorage persistence (`cava_edits`)
- [x] PWA with offline support
- [x] Dark/Light theme, multi-language (ES/EN/PT)

## Phase 2: Backend & Real-Time Sync
- [ ] REST API (Node/Express or Python/FastAPI)
- [ ] Database migration (PostgreSQL or Firebase)
- [ ] Authentication (staff roles: admin, sommelier, viewer)
- [ ] WebSocket-based real-time sync across devices
- [ ] Conflict resolution for concurrent edits
- [ ] Audit log for all changes (who, when, what)
- [ ] Replace localStorage edits with API calls

## Phase 3: SaaS & Multi-Tenant
- [ ] Multi-tenant architecture (each restaurant group = tenant)
- [ ] Onboarding flow for new establishments
- [ ] Dashboard with analytics (stock levels, price trends, sales)
- [ ] Galeria establishment activation (data ready in JSON)
- [ ] PDF/Excel export of wine lists
- [ ] QR code generation for table-side wine menus
- [ ] Stripe integration for subscription billing
