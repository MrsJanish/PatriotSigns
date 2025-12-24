# Patriot Signs - Odoo Long-Term Implementation Plan

> **Last Updated:** 2025-12-23  
> **Target Platform:** Odoo 19 on Odoo.sh  
> **Status:** 🟡 In Progress

---

## Vision Statement

Transform Patriot Signs from manual spreadsheet-based operations into a fully integrated Odoo-powered signage manufacturing business, automating the complete lifecycle from **bid intake** through **production**, **installation**, and **billing**.

---

## Current State (What We Have)

| Component | Status | Notes |
|-----------|--------|-------|
| `patriot_cc_ops` module | ✅ Live | ITB email parsing, PDF viewer, sign tally, Excel export |
| CRM Pipeline | ❌ None | Not using Odoo CRM at all |
| Estimating | ❌ Manual | Spreadsheets and QuickBooks |
| Contracts | ❌ Manual | Paper/email based |
| Manufacturing | ❌ None | No production tracking |
| Accounting | ❌ QuickBooks | Not integrated with Odoo |

---

## Future State (Where We're Going)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           PATRIOT SIGNS IN ODOO 19                          │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐  │
│  │   CRM    │ → │ Project  │ → │   MRP    │ → │  Field   │ → │Invoicing │  │
│  │ Pipeline │   │ Mgmt     │   │Production│   │ Service  │   │ & AR     │  │
│  └──────────┘   └──────────┘   └──────────┘   └──────────┘   └──────────┘  │
│       ↑                                                           │        │
│       │                                                           ↓        │
│  ┌────────────┐                                          ┌──────────────┐  │
│  │ CC Ops     │                                          │  QuickBooks  │  │
│  │ (Enhanced) │                                          │  Connector   │  │
│  └────────────┘                                          └──────────────┘  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Phase Breakdown

### Phase 1: Foundation & CRM (Q1 2025) ✅ In Progress
> **Goal:** Establish proper lead/opportunity pipeline with CC integration

| Task | Odoo Module | Status |
|------|-------------|--------|
| [ ] Migrate `cc.opportunity` → Odoo CRM Lead/Opportunity | `crm` | 🔴 Not Started |
| [/] CC Ops Dashboard (bid intake) | `patriot_cc_ops` | 🟡 Partial |
| [ ] PDF document attachment system | `documents` | 🔴 Not Started |
| [ ] Sign schedule extraction & storage | `patriot_cc_ops` | 🟡 Partial |
| [ ] Contact/Company management (GCs, Owners, Architects) | `contacts` | 🔴 Not Started |

**Automations to Build:**
- Auto-create CRM Lead from parsed ITB email
- Auto-attach documents to opportunity
- Auto-populate GC/Owner from email content

---

### Phase 2: Estimating & Quoting (Q2 2025)
> **Goal:** Replace spreadsheet estimating with Odoo-based system

| Task | Odoo Module | Status |
|------|-------------|--------|
| [ ] Product catalog for sign types | `product` | 🔴 Not Started |
| [ ] Sign Category & Type hierarchy | Custom module | 🔴 Not Started |
| [ ] Bill of Materials (BoM) for sign products | `mrp` | 🔴 Not Started |
| [ ] Quotation templates | `sale` | 🔴 Not Started |
| [ ] Labor cost estimation | `hr_timesheet` | 🔴 Not Started |
| [ ] Material cost tracking | `purchase` | 🔴 Not Started |

**Key Models to Create:**
```
sign.category        (ADA, Wayfinding, Monument, etc.)
sign.type            (RID-1, SN-1, EXT-1, etc.)
sign.element         (Backplate, Letters, Pictogram, etc.)
sign.part            (Physical components per sign)
```

**Automations to Build:**
- Auto-generate BoM from sign type configuration
- Auto-calculate material + labor costs
- Auto-populate quote from bid opportunity

---

### Phase 3: Contracts & Submittals (Q3 2025)
> **Goal:** Track contract signing, insurance, and submittal workflow

| Task | Odoo Module | Status |
|------|-------------|--------|
| [ ] Contract record linked to quotes | `sale` / Custom | 🔴 Not Started |
| [ ] Insurance/COI tracking | Custom module | 🔴 Not Started |
| [ ] Submittal package workflow | `project` | 🔴 Not Started |
| [ ] Shop drawing revision tracking | `documents` | 🔴 Not Started |
| [ ] Approval workflow (Owner → GC → Us) | `approvals` | 🔴 Not Started |
| [ ] Change Order management | Custom module | 🔴 Not Started |

**Automations to Build:**
- Auto-create submittal tasks from confirmed quote
- Auto-notify when COI expires
- Auto-track shop drawing revisions

---

### Phase 4: Manufacturing & Production (Q4 2025)
> **Goal:** Full MRP integration for sign fabrication

| Task | Odoo Module | Status |
|------|-------------|--------|
| [ ] Manufacturing Orders from Sales Orders | `mrp` | 🔴 Not Started |
| [ ] Work Centers (CNC, Print, Assembly, etc.) | `mrp` | 🔴 Not Started |
| [ ] Work Order routing | `mrp` | 🔴 Not Started |
| [ ] Quality Control checkpoints | `quality_mrp` | 🔴 Not Started |
| [ ] Inventory management for materials | `stock` | 🔴 Not Started |
| [ ] Supplier PO integration | `purchase` | 🔴 Not Started |

**Odoo 19 Features to Leverage:**
- Multi-level BoM with component substitution
- Shop floor interface for production workers
- Lot/serial tracking per sign
- IoT integration for machine monitoring

---

### Phase 5: Field Service & Installation (Q1 2026)
> **Goal:** Track installation scheduling and field work

| Task | Odoo Module | Status |
|------|-------------|--------|
| [ ] Installation scheduling | `field_service` | 🔴 Not Started |
| [ ] Install crew assignment | `hr` | 🔴 Not Started |
| [ ] Site-specific delivery tracking | `stock` | 🔴 Not Started |
| [ ] On-site photos & completion confirmation | `field_service` | 🔴 Not Started |
| [ ] Punchlist management | `project` | 🔴 Not Started |

---

### Phase 6: Billing & Accounting Integration (Q2 2026)
> **Goal:** Connect Odoo billing to QuickBooks

| Task | Odoo Module | Status |
|------|-------------|--------|
| [ ] Progress billing (Pay Applications) | `sale` / Custom | 🔴 Not Started |
| [ ] Retainage tracking | Custom module | 🔴 Not Started |
| [ ] QuickBooks Online connector | `account_qbo` | 🔴 Not Started |
| [ ] Invoice sync to QB | Connector | 🔴 Not Started |
| [ ] Payment sync from QB | Connector | 🔴 Not Started |

**Options for QB Integration:**
1. **Odoo Connector (3rd party)** - e.g., Synconics QB connector
2. **API-based sync** - Custom module using QBO API
3. **Migration to Odoo Accounting** - Long-term option

---

## Module Architecture

```
PatriotSigns Repository
├── modules/
│   ├── patriot_intro/          # Welcome screen (existing)
│   ├── patriot_cc_ops/         # CC integration (existing, enhance)
│   ├── patriot_crm/            # CRM customizations (new)
│   ├── patriot_signage/        # Sign catalog & BoM (new)
│   ├── patriot_estimating/     # Estimation engine (new)
│   ├── patriot_submittals/     # Submittal workflow (new)
│   ├── patriot_production/     # MRP customizations (new)
│   ├── patriot_field_service/  # Installation tracking (new)
│   └── patriot_billing/        # Pay apps & QB sync (new)
```

---

## Odoo.sh Deployment Strategy

### Branching Model
```
main (production)
├── staging (pre-production testing)
└── development (active development)
    ├── feature/crm-integration
    ├── feature/sign-catalog
    └── feature/qb-connector
```

### Deployment Workflow
1. Develop on `development` branch
2. Test on staging environment
3. Merge to `main` for production deployment
4. Odoo.sh auto-deploys on push

### Best Practices
- [ ] All modules must have `__manifest__.py`
- [ ] Python dependencies in `requirements.txt`
- [ ] Unit tests for custom logic
- [ ] Code reviews before production merge
- [ ] Modular design - small, focused modules
- [ ] Inherit/extend rather than modify core

---

## Data Migration Plan

| Data Source | Target | Priority |
|-------------|--------|----------|
| Excel bid sheets | CRM Opportunities | High |
| Customer contacts | `res.partner` | High |
| Sign type library | `sign.type` products | Medium |
| Historical quotes | `sale.order` | Medium |
| QB customer list | `res.partner` | Low |
| QB products | `product.product` | Low |

---

## Key Integrations

| External System | Integration Type | Priority |
|----------------|------------------|----------|
| ConstructConnect | API + Email parsing | ✅ Done |
| GitHub Actions | Document fetcher | ✅ Done |
| QuickBooks Online | Connector (TBD) | Phase 6 |
| Email (ITB notifications) | `mail.thread` | ✅ Done |
| Omega (supplier) | Portal access? | Future |

---

## Success Metrics

| Metric | Current | Target |
|--------|---------|--------|
| Time from ITB to quote | ~4 hours manual | < 30 min |
| Sign schedule errors | ~10% rework | < 2% |
| Quote accuracy | Unknown | > 95% |
| Production visibility | None | Real-time |
| Invoice cycle time | ~2 weeks | < 3 days |

---

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Odoo 19 edge cases | Medium | Test thoroughly on staging, report bugs to Odoo |
| QB integration complexity | Medium | Research connectors early |
| User adoption resistance | High | Phased rollout, training |
| Data migration gaps | Medium | Run parallel systems initially |
| Custom dev scope creep | High | Strict phase boundaries |

---

## Team & Responsibilities

| Role | Responsibility | Person |
|------|----------------|--------|
| Project Owner | Decisions, priorities | TBD |
| Odoo Developer | Custom modules | AI + Carter |
| Data Migration | Excel → Odoo | Carter |
| User Training | Process documentation | Carter |
| Testing | UAT on staging | Carter |

---

## Next Steps

See: **[SHORT_TERM_PLAN.md](./SHORT_TERM_PLAN.md)** for immediate action items.

---

## Changelog

| Date | Change |
|------|--------|
| 2025-12-23 | Initial plan created |
