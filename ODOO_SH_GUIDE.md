# Odoo.sh Deployment & Data Persistence Guide

> **CRITICAL WARNING:** Understanding this is essential to preventing data loss.

## The "Data Disappearance" Mystery
You observed that pushing code to GitHub "removes data or configuration" (emails, DNS settings, opportunities).
**This is NOT a bug in the code.** This is a **feature of Odoo.sh Staging branches**.

## How Odoo.sh Branches Work

### 1. Production Branch (`main` / `master`)
*   **Behavior:** Permanent Storage.
*   **Data Persistence:** Data is **NEVER** deleted automatically.
*   **Deploy Action:** When you push code, it restarts the server and updates modules (`-u`). It does **NOT** drop the database.
*   **Use Case:** Real business operations.

### 2. Staging Branches (`staging`)
*   **Behavior:** Ephemeral Testing.
*   **Data Persistence:** **TEMPORARY.**
*   **Deploy Action:** By default, Odoo.sh often **WIPES** the staging database and **RESTORES** a fresh backup from Production.
    *   *Why?* To guarantee you are testing your new code against "Real" data.
    *   *The Consequence:* Any data you manually created on Staging (Opportunities, DNS configs, Emails) since the last push is **DELETE** and overwritten by the copy from Production.
*   **Use Case:** Testing code before merge. **DO NOT enter real business data here.**

### 3. Development Branches (`dev-*`)
*   **Behavior:** Sandbox.
*   **Data Persistence:** Depends on settings, but often recycled.
*   **Use Case:** Coding.

---

## How to Fix Your Problem

### Scenario A: You are trying to "Go Live"
If you are entering real data (Emails, Opportunities) that you want to keep:
1.  **Merge your code to the PRODUCTION branch.**
2.  Enter your data on the **Production** URL (e.g., `omegasignsco.odoo.com`, NOT `omegasignsco-staging.odoo.com`).
3.  Future pushes to Production will **KEEP** this data safe.

### Scenario B: You want to keep data on Staging (Not Recommended)
If you really need your Staging data to survive a push (e.g., for a long demo):
1.  Go to **Odoo.sh Dashboard** > **Branches** > Select your Staging branch.
2.  Look for the **"History"** or **"Settings"** tab.
3.  Change the behavior from "Restore from Production" to "Use current database" (if available) or ensure you are not triggering a "Rebuild".
    *   *Note:* Dragging a branch from Dev to Staging *always* triggers a rebuild.

## Configuration Best Practices
For settings like DNS/API Keys that differ between Staging and Prod:
1.  We have set `noupdate="1"` in your XML files.
2.  **However**, if the database is replaced by a backup from Production (which might be empty), your Staging settings are gone.
3.  **Solution:** Setup your configurations in **Production** first. Then, when Staging rebuilds, it will inherit the correct configurations from Production.
