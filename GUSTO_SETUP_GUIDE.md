# Gusto Integration Guide (Odoo)

This guide walks you through connecting your **Gusto Payroll** to Odoo so that timesheets logged in Odoo can sync to Gusto for payroll processing.

## Prerequisite: The Module
Odoo has a native connector, but it is often an "Enterprise" feature or requires a specific app.

1.  **Go to Apps.**
2.  Search for **"Gusto"**.
3.  Look for **"Gusto US Payroll"** (by Odoo S.A.).
    *   *If found:* Click **Activate/Install**.
    *   *If NOT found:* You may need to enable "Payroll" first, or your Odoo version/edition might require a third-party bridge (like "Syncok" or "Ventor").
    *   *Recommendation:* Use the native Odoo module if available.

---

## Step 1: Generate Gusto Credentials
You need to tell Gusto that Odoo is allowed to talk to it.

1.  Log in to your **Gusto Admin** account (gusto.com).
2.  Go to **Settings** (or Developer Settings if available).
3.  Look for **"API Keys"** or **"Integrations"**.
4.  Create a **New Token/Key**.
    *   **Name:** `Odoo Integration`
    *   **Permissions:** Read/Write (or "Full Access" to Payroll/Employees).
5.  **Copy this Key.** (You will only see it once!).

---

## Step 2: Configure Odoo
1.  In Odoo, go to **Settings > General Settings**.
2.  Search for **"Gusto"** or look under the **Payroll** section.
3.  **Enable Gusto Integration.**
4.  **Paste the API Key** you copied from Gusto.
5.  **Save.**

---

## Step 3: Synching Employees
Odoo needs to know that "Tiffany in Odoo" = "Tiffany in Gusto".

1.  Go to **Payroll > Configuration > Settings**.
2.  Click **"Sync Employees from Gusto"** (if available) OR manually map them:
    *   Open an **Employee** profile in Odoo.
    *   Go to the **HR Settings** or **Payroll** tab.
    *   Look for a **"Gusto Config"** or **"Gusto ID"** field.
    *   Enter their matching email or ID to link them.

---

## Step 4: Testing Timesheets
1.  Have an employee log 1 hour in a Timesheet.
2.  Go to **Payroll > Payslips**.
3.  Create a Payslip for that employee.
4.  Verify that the **Worked Days** or **Inputs** automatically pull that 1 hour from the Timesheet.
    *   *Note:* Ensure the "Project" they logged time to is linked to a valid "Analytic Account" if required by your setup.
