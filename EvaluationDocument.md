# Patriot Signs Odoo Evaluation & Project-Based Timekeeping Strategy
**Date:** December 30, 2025
**Version:** 1.0
**Target Platform:** Odoo 19 (Odoo.sh)

---

## 1. Executive Summary

This document represents a comprehensive "web of understanding" of the current Patriot Signs Odoo infrastructure, codebase, and business objectives. 

**Current Status:** Patriot Signs has laid a strong foundation with a modular Odoo architecture (`patriot_*` modules). The system is currently transitioning from a "ConstructConnect Opportunity" focus (pre-sales) to a full ERP implementation (execution). 

**The Critical Gap:** While high-level project management (`patriot_projects`) and production batching (`patriot_production`) exist as data structures, there is **zero implementation of granular timekeeping**. The system currently tracks *dates* (Start/End) but not *labor hours*.

**The Strategic Pivot:** To achieve "Project-Based Timekeeping," we must shift from treating Projects/Production Orders as static headers to treating them as **Work Containers** filled with assignable tasks (Design, Fabrication, Installation) against which employees verify time via Kiosk or Mobile.

---

## 2. Infrastructure & Codebase Audit ("The Web of Understanding")

We have indexed the entire codebase. The project follows a clean, modular structure, which is best practice for Odoo.sh.

### 2.1 Module Architecture
The repository is divided into functional domains. Here is the mesh of dependencies:

| Module | Status | Role | Key Dependencies |
| :--- | :--- | :--- | :--- |
| **`patriot_cc_ops`** | 🟢 **Active** | **The Core.** Handles ITB ingestion, PDF parsing & Bid intake. | `patriot_signage`, `crm` |
| **`patriot_projects`** | 🟡 **Skeleton** | **The Container.** Inherits `project.project`. Holds Contract/Owner info. | `project`, `hr_timesheet` |
| **`patriot_production`** | 🟡 **Skeleton** | **The Factory.** Custom `ps.production.order`. Links to `mrp`. | `mrp` |
| **`patriot_signage`** | 🟢 **Foundation** | **The Product.** Defines `sign.type` and `sign.instance`. | `base` |
| **`patriot_crm`** | 🟡 **In Progress** | **The Pipeline.** Transitioning `cc.opportunity` to `crm.lead`. | `crm` |
| **`patriot_field_service`** | 🔴 **Empty** | **The Site.** Placeholder for installation logic. | `industry_fsm` |

### 2.2 Findings & Technical Debt
1.  **Duplicate Object Models:** `cc.opportunity` (in `cc_ops`) and `crm.lead` (standard) act as two separate "Bid" records. *Action:* The migration plan to unify these is correct and urgent.
2.  **Missing Task Layer:** `patriot_projects` converts a Won Opportunity into a `project.project` but **does not create Tasks**. Time tracking in Odoo happens on **Tasks**, not Projects. This is the root cause of the timekeeping gap.
3.  **Production Disconnect:** `ps.production.order` acts as a "wrapper" around standard `mrp.production`. It tracks status (`design`, `fabrication`) but these are purely state fields, not trackable work orders.

### 2.3 Odoo 19 Readiness
The codebase structure (`manifest.py`, folders) is modern. However, Odoo 19 introduces stricter "Owl" JS framework requirements. The `patriot_cc_ops` dashboard uses some custom JS that must be verified against Odoo 19's Owl Component system. The new **Odoo 19 Gantt & Project features** (Advanced Time Tracking) are native modules we are currently *under-utilizing*.

---

## 3. Business Context & Industry Alignment

### 3.1 External Entity Research
*   **Omega Signs Co:** Identified as a key relationship (likely supplier or strategic partner). In the Sign Industry, outsourcing fabrication of specialized signage (e.g., massive pylons, complex neon) is common. *Implication:* Our system needs a "Sub-Contractor" feature in Timekeeping/Project management to track outsourced costs vs internal labor.
*   **Patriot ADA Signs/Patriot Signage:** This is **Us**. We specialize in high-volume, regulation-heavy signage (ADA, Wayfinding). *Implication:* This business model is **Project-Based, not Product-Based**. We don't make 1,000 widgets to stock; we make 1 custom sign package for 1 specific building.

### 3.2 The "Project-Based Timekeeping" Mandate
In a custom manufacturing business (Signage, Cabinetry), Profitability = Bid Price - (materials + **LABOR**).
Currently, we know the Bid Price. We can estimate Materials. **We are blind on Labor.**

**We need to answer:**
*   "Did the *University Hospital* job lose money because Fabrication took 4x longer than estimated?"
*   "Is the *Design Team* spending 20 hours on $500 orders?"

---

## 3.3 Deployment & Data Safety (Crucial Finding)
**Issue:** Pushing to Odoo.sh Staging wipes "manually created data" (DNS, Opportunities).
**Diagnosis:** This is standard Odoo.sh behavior. Staging branches are ephemeral and often strictly rebuild from Production backups.
**Solution:**
1.  See **[ODOO_SH_GUIDE.md](./ODOO_SH_GUIDE.md)** for detailed protocols.
2.  **Rule:** Never treat Staging as storage. Merge to Production for data persistence.
3.  **Code Safety:** We confirmed all configuration files use correctly set `noupdate="1"` to prevent code-based overwrites.

---

## 4. Evaluation: Gaps & Requirements

### 4.1 What We Have
*   **Containers:** We have the `Project` (Contract) and `Production Order` (Batch).
*   **Dates:** We know when things *should* happen (`submittals_due`, `install_start`).
*   **Sign Data:** We have excellent data on *what* we are making (`sign.type`, `sign.instance`).

### 4.2 What We Need (The Gap)
1.  **Task Automation:** When a Project is confirmed, the system must automatically generate:
    *   *Task 1: Project Management (PM)*
    *   *Task 2: Design & Submittals*
    *   *Task 3: Production (Linked to MRP)*
    *   *Task 4: Installation (Linked to FSM)*
2.  **Timesheet Integration:**
    *   **Project Managers** log time to Task 1 via Desktop.
    *   **Designers** log time to Task 2 via Desktop/Plugin.
    *   **Fabricators** log time to Task 3 via **Kiosk Mode** (iPad in shop).
    *   **Installers** log time to Task 4 via **Mobile App** (GPS verified).
3.  **Budget vs Actual:** We need to set an "Initially Planned Hours" on these tasks to compare against "Actual Timesheet Entries" in real-time.

---

## 5. Strategic Implementation Plan: Project-Based Timekeeping

This is the roadmap to solve the priority request.

### Phase 1: Data Model Realignment (Architecture)
**Objective:** Bridge `patriot_projects` to specific work units.

*   **Action 1: Define Service Products.** Create Product Records for "Design Services", "Project Management", "Installation Labor".
*   **Action 2: Configure "Service Tracking".** Set these products to "Create a Task in Project" upon Sales Order Confirmation.
*   **Action 3: Master Project Template.** Create a "Standard Signage Project" template in Odoo with pre-defined Stages (New, In Progress, On Hold, Done) and pre-defined Task structures.

### Phase 2: The "Shop Floor" Timekeeping (Fabrication)
**Objective:** Capture factory labor without slowing down production.

*   **Mechanism:** Use Odoo **Manufacturing Work Orders**.
*   **Change:** Instead of just a generic `ps.production.order`, we will generate `mrp.production` records.
*   **Workflow:**
    1.  `ps.production.order` (Batch) is released.
    2.  System generates `mrp.workorder` operations (Cut, Paint, Assembly).
    3.  Shop employees scan a barcode on the traveler (paper).
    4.  Odoo Kiosk logs them "In". When finished, they scan "Out".
    *   *Result:* Precision labor cost per batch, automatically rolled up to the Project.

### Phase 3: The "Field" Timekeeping (Installation)
**Objective:** Capture crew time on site.

*   **Mechanism:** **Odoo Field Service (Industry FSM)**.
*   **Change:** `patriot_field_service` must inherit `industry_fsm`.
*   **Workflow:**
    1.  Project Installation Date arrives.
    2.  System creates a `project.task` tagged as 'Field Service'.
    3.  Installer opens Odoo Mobile App.
    4.  Clicks "Start Journey" (Travel time) -> "Start Work" (Install time) -> "Sign off" (Client Signature).
    *   *Result:* Travel vs Labor breakdown, automatically billed or costed to the project.

### Phase 4: Reporting & Dashboarding
*   **Project Profitability Report:** (Native Odoo 19). A single view showing:
    *   Revenue (Sales Order)
    *   - Material Cost (Stock Moves)
    *   - Labor Cost (Timesheets * Employee Rate)
    *   = **Real Margin**

---

## 6. Immediate Next Steps (Action Items)

To start "Project-Based Timekeeping" immediately:

1.  **Configure the "Project Services" Products:**
    *   Create a product "Signage Production Labor".
    *   Set *Service Tracking*: "Create a task in sales order's project".
2.  **Modify `patriot_projects`:**
    *   Add `allow_timesheets = True` default on creation.
    *   Add a logic hook: When `project_stage` moves to 'Production', ensure the 'Production Task' exists.
3.  **Activate "Analytic Accounting":**
    *   Ensure every Project gets an Analytic Account automatically. This is the "bucket" that catches all costs.

**Recommendation:**
Proceed immediately to **Phase 1 (Data Model Realignment)**. We do not need new Python code yet; we need *Configuration* and *Product Setup* to prove the flow, then we write the automation code in `patriot_projects` to force this structure on every new job.
