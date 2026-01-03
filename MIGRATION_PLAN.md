# 28-Day Migration Plan: Patriot Signs

**Start Date:** January 6, 2026  
**Go-Live Target:** February 3, 2026

---

## Week 1: Foundation (Jan 6-10)
| Day | Focus |
|-----|-------|
| Mon | **Timekeeping Live** – Verify staging; push to production; train employees on Start/Stop |
| Tue | **Gusto Setup** – Connect Odoo <-> Gusto; sync employees; test 1 timesheet entry |
| Wed | Clean up CRM Stages; migrate existing Opportunities from Odoo Online |
| Thu | Set up Email (M365 Alias finalized); configure outgoing mail templates |
| Fri | *Buffer / Testing* |

---

## Week 2: Core Workflow (Jan 13-17)
| Day | Focus |
|-----|-------|
| Mon | **Estimating Module** – Verify pricing logic; fix any sign cost bugs |
| Tue | **Sales Quotes** – Link Estimates to Sales Orders; confirm PDF generation |
| Wed | **Projects** – Test full flow: Won Opportunity → Project Created → Tasks Ready |
| Thu | **Submittals** – Verify submittal creation and tracking |
| Fri | *Buffer / Testing* |

---

## Week 3: Production & Field (Jan 20-24)
| Day | Focus |
|-----|-------|
| Mon | **Manufacturing** – Set up BOMs for common sign types |
| Tue | **Production Orders** – Test `ps.production.order` integration with `mrp.production` |
| Wed | **Field Service** – Configure mobile app for Installers |
| Thu | **Inventory** – Initial stock setup (substrates, hardware) |
| Fri | *Buffer / Testing* |

---

## Week 4: Go-Live (Jan 27-31)
| Day | Focus |
|-----|-------|
| Mon | **Final Data Migration** – Export all live data from Odoo Online; import to Production |
| Tue | **User Training** – All hands session on new system |
| Wed | **Go-Live Day** – Switch DNS; decommission old system |
| Thu | **Monitoring** – Watch for errors; hot-fix anything broken |
| Fri | **Retroactive** – Address user feedback; minor tweaks |

---

## Post Go-Live (Feb 3+)
- Continuous improvement based on real usage
- Phase 2: Advanced Reporting, Dashboards, Integrations
