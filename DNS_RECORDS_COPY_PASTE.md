# DNS Records Table

Here are the records formatted exactly for a **Type | Name | Data | TTL** view.

| Type | Name | Data (Value) | TTL |
| :--- | :--- | :--- | :--- |
| **MX** | `@` | `0 patriotadasigns-com.mail.protection.outlook.com` | 1 Hour |
| **TXT** | `@` | `v=spf1 include:_spf.odoo.com include:spf.protection.outlook.com ~all` | 1 Hour |
| **CNAME** | `autodiscover` | `autodiscover.outlook.com` | 1 Hour |
| **CNAME** | `sip` | `sipdir.online.lync.com` | 1 Hour |
| **CNAME** | `lyncdiscover` | `webdir.online.lync.com` | 1 Hour |
| **CNAME** | `enterpriseregistration` | `enterpriseregistration.windows.net` | 1 Hour |
| **CNAME** | `enterpriseenrollment` | `enterpriseenrollment-s.manage.microsoft.com` | 1 Hour |
| **SRV** | `_sip._tls` | `100 1 443 sipdir.online.lync.com` | 1 Hour |
| **SRV** | `_sipfederationtls._tcp` | `100 1 5061 sipfed.online.lync.com` | 1 Hour |

> **Note on SRV Records:**
> If your DNS provider asks for separate fields for Service/Protocol/Port/Weight:
> *   **Record 1:** Service=`_sip`, Protocol=`_tls`, Priority=`100`, Weight=`1`, Port=`443`, Target=`sipdir.online.lync.com`
> *   **Record 2:** Service=`_sipfederationtls`, Protocol=`_tcp`, Priority=`100`, Weight=`1`, Port=`5061`, Target=`sipfed.online.lync.com`
