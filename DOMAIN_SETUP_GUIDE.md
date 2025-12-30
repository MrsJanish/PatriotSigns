# Domain & Email Setup Guide (Patriot ADA Signs)

> **Objective:** Switch from `patriotsigns.odoo.com` to `patriotadasigns.com` and issue employee emails.

---

## 1. Domain Configuration (DNS)

To point `patriotadasigns.com` to your Odoo instance:

### Step 1: Configure Odoo.sh
1.  Go to your **Odoo.sh Dashboard**.
2.  Select the **Production** branch settings (Deployment tab).
3.  Find **"Domains"**.
### Step 3: SPF Record (CRITICAL - MERGE ONLY)
**Do not create a second SPF record.** You already made one for Odoo.
You must **EDIT** the existing `@` TXT record to include *both* systems.

*   **Bad (Two records):**
    *   `v=spf1 include:_spf.odoo.com ~all`
    *   `v=spf1 include:spf.protection.outlook.com -all`
*   **Good (Merged Record):**
    *   Value: `v=spf1 include:_spf.odoo.com include:spf.protection.outlook.com ~all`

### Step 4: Add the Rest
Add the specific MX, CNAME, and SRV records Microsoft gave you exactly as shown.

### Step 2: Configure Registrar (GoDaddy/Namecheap/etc)
1.  Log in to where you bought the domain.
2.  **CNAME Record** (Crucial):
    *   **Action:** If a `www` record already exists (pointing to `patriotadasigns.com` or `@`), **EDIT** or **DELETE** it.
    *   **Type:** `CNAME`
    *   **Name / Host:** `www`
    *   **Value / Target:** `patriotsigns.odoo.com`
    *   **TTL:** 1 Hour (or Automatic)
3.  **Forwarding** (For the "naked" domain):
    *   Look for "Forwarding" or "Domain Redirect" in your registrar.
    *   Forward `patriotadasigns.com` (http & https) to `https://www.patriotadasigns.com`.
    *   *Note: usage of A Records for naked domains on Odoo.sh is possible (IP: 51.161.xx.xx) but Forwarding is often more reliable for handling SSL certification.*

### Step 3: Configure Database
1.  Log in to Odoo as Administrator.
2.  Go to **Settings** > **Website**.
3.  Set "Domain" to `https://www.patriotadasigns.com`.
4.  Activate "Redirect to this domain" to force traffic there.

---

## 2. Email Configuration

### Step 1: Mail Gateway (Incoming/Outgoing)
Odoo.sh handles this automatically *if* the domain is verified.
1.  Go to **Settings** > **General Settings**.
2.  Under **Alias Domain**, enter `patriotadasigns.com`.
3.  Save.
4.  (Optional but Recommended) Setup SPF/DKIM/DMARC in your DNS to prevent spam folders.
    *   **SPF (TXT Record):** `v=spf1 include:_spf.odoo.com ~all`
    *   **DKIM:** Get the DKIM key from Odoo Technical Settings.

### Step 2: Issue Employee Emails
You manually creating users in Odoo triggers the "Invitation Email".

**Instructions:**
1.  Go to **Settings** > **Users & Companies** > **Users**.
2.  Click **New**.
3.  **Name:** `John Doe`
4.  **Email:** `john@patriotadasigns.com`
5.  **Access Rights:** Select "Internal User" and grant Project/Manufacturing access.
6.  Click **Save**.
7.  Click **"Send Invitation Email"** (at the top).

---

## 3. Email Hosting (Microsoft 365)
Since you are adding this domain to an existing M365 tenant (`omegasignsco.com`):

1.  **Log in to Microsoft 365 Admin Center** (admin.microsoft.com).
2.  Go to **Settings > Domains**.
3.  Click **Add Domain** and type `patriotadasigns.com`.
4.  Microsoft will ask you to verify ownership (usually by adding a TXT record in GoDaddy).
5.  Once verified, Microsoft will give you **MX Records**.
6.  **Add these MX Records** to your GoDaddy/Registrar (just like you did the CNAME).
    *   *Note:* This routes incoming emails to Outlook, not Odoo (which is what you want).
7.  **Create Users:** In M365, create `tiffany@patriotadasigns.com` (or add it as an alias to your existing user).

---

## 4. Data File (Bulk Import Option)
If you have many employees, we can load them via CSV/XML.

**Example `users.csv`:**
```csv
name,login,email,groups_id
John Doe,john@patriotadasigns.com,john@patriotadasigns.com,base.group_user
Jane Smith,jane@patriotadasigns.com,jane@patriotadasigns.com,base.group_user
```
Import this file in the Users menu.
