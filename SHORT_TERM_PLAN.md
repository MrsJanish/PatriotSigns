# Patriot Signs - Short-Term Implementation Plan

> **Sprint:** Phase 1.1 - CRM Integration Foundation  
> **Duration:** 2 weeks  
> **Start Date:** 2025-12-23  
> **Goal:** Migrate CC Opportunities to proper Odoo CRM pipeline

---

## Background

Currently, the `patriot_cc_ops` module creates records in a custom `cc.opportunity` model that is completely separate from Odoo's native CRM. This means:

- ❌ No CRM pipeline visibility
- ❌ No proper lead/opportunity stages  
- ❌ No CRM reporting or forecasting
- ❌ Contacts stored as text fields, not linked

This sprint integrates with Odoo's native `crm.lead` model while keeping the CC-specific functionality.

---

## Proposed Changes

### Component 1: Model Migration

#### [MODIFY] `cc_opportunity.py`

**Current State:**
- Custom `cc.opportunity` model with `_inherit = ['mail.thread', 'mail.activity.mixin']`
- Stores GC, Owner, Architect as text fields
- Has custom stages: `new`, `fetching`, `ready`, `reviewing`, `quoting`, `submitted`

**Changes:**
1. Replace `cc.opportunity` → extend `crm.lead` with CC-specific fields
2. Move GC/Owner/Architect to proper `res.partner` Many2one links
3. Keep PDF attachment and sign type functionality

```python
# New approach - inherit crm.lead
class CCOpportunity(models.Model):
    _inherit = 'crm.lead'
    
    # CC-specific fields
    cc_project_id = fields.Char("CC Project ID")
    cc_access_code = fields.Char("Access Code")
    cc_source_url = fields.Char("Source URL")
    bid_date = fields.Date("Bid Date")
    
    # Linked contacts (not text)
    gc_partner_id = fields.Many2one('res.partner', "General Contractor")
    owner_partner_id = fields.Many2one('res.partner', "Owner")
    architect_partner_id = fields.Many2one('res.partner', "Architect")
    
    # Keep existing relationships
    sign_type_ids = fields.One2many('cc.sign.type', 'opportunity_id')
```

---

#### [MODIFY] `sign_type.py`

**Changes:**
- Update `opportunity_id` foreign key: `cc.opportunity` → `crm.lead`

```python
class SignType(models.Model):
    _name = 'cc.sign.type'
    
    opportunity_id = fields.Many2one(
        'crm.lead',  # Changed from 'cc.opportunity'
        string='Opportunity',
        required=True,
        ondelete='cascade'
    )
```

---

### Component 2: CRM Pipeline Stages

#### [NEW] `data/crm_stages.xml`

Create CC-specific pipeline stages:

```xml
<record id="stage_cc_new" model="crm.stage">
    <field name="name">📧 New ITB</field>
    <field name="sequence">10</field>
</record>
<record id="stage_cc_fetching" model="crm.stage">
    <field name="name">📥 Fetching Docs</field>
    <field name="sequence">20</field>
</record>
<record id="stage_cc_reviewing" model="crm.stage">
    <field name="name">📄 Reviewing</field>
    <field name="sequence">30</field>
</record>
<!-- more stages -->
```

---

### Component 3: View Updates

#### [MODIFY] `views/cc_opportunity_views.xml`

- Update form view to use `crm.lead` base form
- Keep CC-specific fields in custom page/group
- Update kanban view for new stage structure

---

### Component 4: Dashboard Update

#### [MODIFY] `static/src/js/cc_ops_dashboard.js`

- Change ORM calls from `cc.opportunity` → `crm.lead`
- Filter by CC opportunities using domain (e.g., `cc_project_id != False`)

---

### Component 5: Contact Auto-Creation

#### [NEW] Logic in `message_new()`

When parsing ITB email, auto-create contacts if not found:

```python
def _get_or_create_partner(self, name, type='gc'):
    """Find or create partner by name"""
    Partner = self.env['res.partner']
    partner = Partner.search([('name', 'ilike', name)], limit=1)
    if not partner and name:
        partner = Partner.create({
            'name': name,
            'is_company': True,
            'company_type': 'company',
            'category_id': [(4, self._get_gc_category().id)] if type == 'gc' else [],
        })
    return partner
```

---

## Migration Script

#### [NEW] `scripts/migrate_cc_to_crm.py`

One-time migration of existing `cc.opportunity` records to `crm.lead`:

```python
# Pseudocode
for old_opp in cc_opportunity.search([]):
    new_lead = crm_lead.create({
        'name': old_opp.name,
        'cc_project_id': old_opp.project_number,
        'description': old_opp.description,
        # ... map all fields
    })
    # Update sign_type_ids to point to new_lead
    old_opp.sign_type_ids.write({'opportunity_id': new_lead.id})
```

---

## Files Changed Summary

| File | Action | Complexity |
|------|--------|------------|
| `models/cc_opportunity.py` | Major refactor | 🔴 High |
| `models/sign_type.py` | Minor update | 🟢 Low |
| `data/crm_stages.xml` | New file | 🟢 Low |
| `views/cc_opportunity_views.xml` | Significant update | 🟡 Medium |
| `static/src/js/cc_ops_dashboard.js` | Model name change | 🟢 Low |
| `static/src/js/sign_tally.js` | Model name change | 🟢 Low |
| `scripts/migrate_cc_to_crm.py` | New file | 🟡 Medium |
| `__manifest__.py` | Add dependencies | 🟢 Low |

---

## Verification Plan

### Automated Testing

> ⚠️ **No existing tests found** - Need to create basic test suite

#### [NEW] `tests/test_cc_crm_integration.py`

```python
def test_itb_email_creates_crm_lead(self):
    """Email parsing creates crm.lead with CC fields"""
    
def test_gc_contact_auto_created(self):
    """GC name creates res.partner if not exists"""
    
def test_sign_types_linked_to_lead(self):
    """Sign types properly linked to crm.lead"""
```

**Run command:**
```bash
odoo-bin -c odoo.conf -u patriot_cc_ops --test-enable --stop-after-init
```

---

### Manual Testing (Staging Environment)

1. **Email Parsing Test**
   - Send test ITB email to staging alias
   - Verify CRM lead created with correct data
   - Check GC/Owner/Architect as linked contacts

2. **Dashboard Test**
   - Open CC Dashboard
   - Verify projects display correctly
   - Click project → opens CRM lead form

3. **Sign Tally Test**
   - Open Sign Tally from a lead
   - Add/edit sign types
   - Verify quantities persist

4. **Document Test**
   - Trigger document fetch
   - Verify PDFs attached to CRM lead
   - PDF viewer opens correctly

---

## Risks

| Risk | Mitigation |
|------|------------|
| Data loss during migration | Backup database before running script |
| Breaking PDF viewer | Test extensively in staging |
| Sign types orphaned | Migration script updates references |

---

## Definition of Done

- [ ] `crm.lead` model extended with CC fields
- [ ] Existing CC opportunities migrated
- [ ] Sign types link to `crm.lead`
- [ ] Dashboard shows projects from `crm.lead`
- [ ] PDF viewer works from CRM lead
- [ ] Contacts created/linked properly
- [ ] All manual tests pass on staging

---

## Estimated Effort

| Task | Hours |
|------|-------|
| Model refactoring | 4h |
| View updates | 3h |
| Dashboard/JS updates | 2h |
| Migration script | 2h |
| Testing | 3h |
| **Total** | **14h** |

---

## Next Sprint Preview

After this sprint, the next step will be:
- **Phase 1.2:** Contact Management Enhancement
  - GC partner categories/tags
  - Contact search/deduplication
  - Partner portal access for GCs
