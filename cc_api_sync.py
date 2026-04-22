#!/usr/bin/env python3
"""
ConstructConnect API → Odoo CRM Sync Worker

Polls the ConstructConnect ProjectLeads API for new construction projects
and creates/updates CRM leads in Odoo via XML-RPC.

Usage:
    python cc_api_sync.py                  # Full sync
    python cc_api_sync.py --dry-run        # Preview only, no Odoo writes
    python cc_api_sync.py --days 7         # Only projects updated in last 7 days

Environment Variables:
    CC_API_KEY      - ConstructConnect API key
    ODOO_URL        - Odoo instance URL
    ODOO_DB         - Odoo database name
    ODOO_USER       - Odoo username
    ODOO_PASSWORD   - Odoo password/API key
"""

import os
import sys
import json
import argparse
import logging
from datetime import datetime, timedelta, timezone
import xmlrpc.client

try:
    import requests
except ImportError:
    print("ERROR: 'requests' package required. Install with: pip install requests")
    sys.exit(1)

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
CC_API_BASE = "https://api.io.constructconnect.com"
CC_API_KEY = os.environ.get("CC_API_KEY", "")

ODOO_URL = os.environ.get("ODOO_URL", "")
ODOO_DB = os.environ.get("ODOO_DB", "")
ODOO_USER = os.environ.get("ODOO_USER", "")
ODOO_PASSWORD = os.environ.get("ODOO_PASSWORD", "")

# Default search filters — adjust to your service area / trade
DEFAULT_STATES = ["OK", "TX", "AR", "KS", "MO"]
DEFAULT_CSI_DIVISIONS = ["10"]  # Division 10 = Specialties (Signage)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("cc_sync")

# ---------------------------------------------------------------------------
# ConstructConnect API Client
# ---------------------------------------------------------------------------

class CCApiClient:
    """Thin wrapper around the ConstructConnect REST API."""

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.session = requests.Session()
        self.session.headers.update({
            "Content-Type": "application/json",
            "Accept": "application/json",
        })

    def search_projects(
        self,
        states: list[str] | None = None,
        csi_divisions: list[str] | None = None,
        updated_since: str | None = None,
        bid_date_from: str | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> dict:
        """
        Search for project leads.

        The exact request/response schema depends on your CC API version.
        This is built from the Postman collection at:
        https://documenter.getpostman.com/view/2373665/U16nMQe3

        Adjust the payload keys once you've made a real test call
        and confirmed the actual field names.
        """
        url = f"{CC_API_BASE}/search/v1/ProjectLeads"
        params = {"x-api-key": self.api_key}

        # Build search payload — field names are best-guess from docs.
        # TODO: Confirm exact payload structure with a live API call.
        payload = {
            "page": page,
            "pageSize": page_size,
        }

        if states:
            payload["states"] = states
        if csi_divisions:
            payload["csiDivisions"] = csi_divisions
        if updated_since:
            payload["updatedSince"] = updated_since
        if bid_date_from:
            payload["bidDateFrom"] = bid_date_from

        log.info(f"CC API → POST {url}  (page={page}, states={states})")
        log.debug(f"Payload: {json.dumps(payload, indent=2)}")

        resp = self.session.post(url, params=params, json=payload, timeout=30)
        resp.raise_for_status()
        data = resp.json()

        # Log summary
        results = data.get("results", data.get("data", []))
        total = data.get("totalResults", data.get("total", len(results)))
        log.info(f"CC API ← {len(results)} results (total: {total})")

        return data

    def get_project(self, project_id: str) -> dict:
        """Get a single project's full details."""
        url = f"{CC_API_BASE}/search/v1/ProjectLeads/{project_id}"
        params = {"x-api-key": self.api_key}
        resp = self.session.get(url, params=params, timeout=30)
        resp.raise_for_status()
        return resp.json()


# ---------------------------------------------------------------------------
# Odoo XML-RPC Client
# ---------------------------------------------------------------------------

class OdooClient:
    """Minimal Odoo XML-RPC wrapper for CRM operations."""

    def __init__(self, url: str, db: str, user: str, password: str):
        self.url = url.rstrip("/")
        self.db = db
        self.user = user
        self.password = password
        self.uid = None
        self.models = None

    def connect(self):
        """Authenticate and store UID."""
        common = xmlrpc.client.ServerProxy(f"{self.url}/xmlrpc/2/common")
        self.uid = common.authenticate(self.db, self.user, self.password, {})
        if not self.uid:
            raise RuntimeError("Odoo authentication failed. Check credentials.")
        self.models = xmlrpc.client.ServerProxy(f"{self.url}/xmlrpc/2/object")
        log.info(f"Odoo ← Connected as UID {self.uid} on {self.db}")

    def execute(self, model: str, method: str, *args, **kwargs):
        """Call execute_kw on the Odoo models proxy."""
        return self.models.execute_kw(
            self.db, self.uid, self.password,
            model, method, list(args), kwargs
        )

    def search_read(self, model: str, domain: list, fields: list, limit: int = 0):
        return self.execute(model, "search_read", domain, fields=fields, limit=limit)

    def search(self, model: str, domain: list, limit: int = 0):
        return self.execute(model, "search", domain, limit=limit)

    def create(self, model: str, values: dict) -> int:
        return self.execute(model, "create", values)

    def write(self, model: str, ids: list, values: dict):
        return self.execute(model, "write", ids, values)

    def find_lead_by_cc_id(self, cc_project_id: str) -> dict | None:
        """Find an existing CRM lead by ConstructConnect project ID."""
        results = self.search_read(
            "crm.lead",
            [["x_cc_project_id", "=", cc_project_id]],
            ["id", "name", "x_cc_project_id", "x_cc_synced_at"],
            limit=1,
        )
        return results[0] if results else None

    def find_or_create_partner(self, name: str, is_company: bool = True) -> int:
        """Find partner by name or create a new one."""
        if not name or not name.strip():
            return False

        name = name.strip()
        results = self.search_read(
            "res.partner",
            [["name", "ilike", name], ["is_company", "=", is_company]],
            ["id", "name"],
            limit=1,
        )
        if results:
            return results[0]["id"]

        # Create new partner
        partner_id = self.create("res.partner", {
            "name": name,
            "is_company": is_company,
        })
        log.info(f"  Created new partner: {name} (ID: {partner_id})")
        return partner_id

    def find_state_id(self, state_code: str) -> int | None:
        """Find res.country.state ID by code (e.g., 'OK', 'TX')."""
        if not state_code:
            return None
        results = self.search_read(
            "res.country.state",
            [["code", "=", state_code.upper()], ["country_id.code", "=", "US"]],
            ["id"],
            limit=1,
        )
        return results[0]["id"] if results else None


# ---------------------------------------------------------------------------
# Field Mapping: CC API → Odoo crm.lead
# ---------------------------------------------------------------------------

def map_project_to_lead(project: dict, odoo: OdooClient) -> dict:
    """
    Map a ConstructConnect project dict to Odoo crm.lead field values.

    ⚠️  The field names below (project['title'], project['bidDate'], etc.)
    are BEST GUESSES based on CC platform features. Once you make a real
    API call and see the actual response JSON, update these keys.

    Run with --dry-run first to see the raw API response and adjust.
    """

    # --- Extract raw values (adjust keys to match actual API response) ---
    cc_id = str(project.get("id", project.get("projectId", "")))
    title = project.get("title", project.get("projectName", "Untitled CC Project"))
    bid_date = project.get("bidDate", project.get("bidDateTime", None))
    project_value = project.get("estimatedValue", project.get("valuation", 0))
    project_stage = project.get("stage", project.get("projectStage", ""))
    project_type = project.get("type", project.get("projectType", ""))
    description = project.get("description", project.get("scope", ""))

    # Address
    address = project.get("address", project.get("location", {}))
    if isinstance(address, dict):
        street = address.get("street", address.get("address1", ""))
        city = address.get("city", "")
        state_code = address.get("state", address.get("stateCode", ""))
        zip_code = address.get("zip", address.get("postalCode", ""))
        county = address.get("county", "")
    else:
        street = project.get("street", project.get("address", ""))
        city = project.get("city", "")
        state_code = project.get("state", project.get("stateCode", ""))
        zip_code = project.get("zip", project.get("postalCode", ""))
        county = project.get("county", "")

    # Contacts / Companies
    gc_name = project.get("gcName", project.get("generalContractor", ""))
    owner_name = project.get("ownerName", project.get("owner", ""))
    architect_name = project.get("architectName", project.get("architect", ""))

    # Contact info
    contact_name = project.get("contactName", project.get("contact", ""))
    phone = project.get("contactPhone", project.get("phone", ""))
    email = project.get("contactEmail", project.get("email", ""))

    # CC metadata
    source_url = project.get("url", project.get("projectUrl", ""))
    doc_count = project.get("documentCount", project.get("planCount", 0))
    addenda_count = project.get("addendaCount", 0)
    csi_divisions = project.get("csiDivisions", project.get("divisions", []))
    last_updated = project.get("lastUpdated", project.get("updatedDate", ""))

    # --- Build Odoo values dict ---
    values = {
        # Core CRM fields
        "name": title,
        "type": "opportunity",
        "description": description or False,
        "contact_name": contact_name or False,
        "phone": phone or False,
        "email_from": email or False,
        "street": street or False,
        "city": city or False,
        "zip": zip_code or False,

        # CC-specific custom fields
        "x_cc_project_id": cc_id,
        "x_cc_source_url": source_url or False,
        "x_cc_doc_count": int(doc_count) if doc_count else 0,
        "x_cc_synced_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),

        # GC/Owner/Architect names are linked via partner records below
        # (partner_id, x_studio_owner, x_studio_architect)
    }

    # Revenue
    if project_value:
        try:
            values["expected_revenue"] = float(project_value)
        except (ValueError, TypeError):
            pass

    # Bid date → x_studio_bid_date (already exists)
    if bid_date:
        try:
            # Handle various date formats from API
            if "T" in str(bid_date):
                parsed = datetime.fromisoformat(str(bid_date).replace("Z", "+00:00"))
                values["x_studio_bid_date"] = parsed.strftime("%Y-%m-%d")
            else:
                values["x_studio_bid_date"] = str(bid_date)[:10]
        except (ValueError, TypeError):
            pass

    # State lookup
    if state_code:
        state_id = odoo.find_state_id(state_code)
        if state_id:
            values["state_id"] = state_id

    # CSI Divisions as comma-separated text
    if csi_divisions:
        if isinstance(csi_divisions, list):
            csi_text = ", ".join(str(d) for d in csi_divisions)
        else:
            csi_text = str(csi_divisions)
        # Store in description if no dedicated field, or we could add one later

    # Partner linking (GC → partner_id, Owner, Architect)
    if gc_name:
        gc_partner_id = odoo.find_or_create_partner(gc_name)
        if gc_partner_id:
            values["partner_id"] = gc_partner_id

    if owner_name:
        owner_partner_id = odoo.find_or_create_partner(owner_name)
        if owner_partner_id:
            values["x_studio_owner"] = owner_partner_id

    if architect_name:
        arch_partner_id = odoo.find_or_create_partner(architect_name)
        if arch_partner_id:
            values["x_studio_architect"] = arch_partner_id

    # Plans site URL
    if source_url:
        values["x_studio_plans_site"] = source_url

    return values


# ---------------------------------------------------------------------------
# Sync Logic
# ---------------------------------------------------------------------------

def sync(args):
    """Main sync loop: pull from CC API, push to Odoo."""

    # Validate credentials
    if not CC_API_KEY:
        log.error("CC_API_KEY environment variable is not set!")
        sys.exit(1)
    if not all([ODOO_URL, ODOO_DB, ODOO_USER, ODOO_PASSWORD]):
        log.error("Missing Odoo credentials (ODOO_URL, ODOO_DB, ODOO_USER, ODOO_PASSWORD)")
        sys.exit(1)

    # Init clients
    cc = CCApiClient(CC_API_KEY)
    odoo = OdooClient(ODOO_URL, ODOO_DB, ODOO_USER, ODOO_PASSWORD)

    if not args.dry_run:
        odoo.connect()

    # Build date filter
    updated_since = None
    bid_date_from = None
    if args.days:
        cutoff = datetime.now(timezone.utc) - timedelta(days=args.days)
        updated_since = cutoff.strftime("%Y-%m-%d")
        log.info(f"Filtering: projects updated since {updated_since}")

    # Counters
    created = 0
    updated = 0
    skipped = 0
    errors = 0
    page = 1

    while True:
        # Fetch page of results from CC
        try:
            data = cc.search_projects(
                states=DEFAULT_STATES,
                csi_divisions=DEFAULT_CSI_DIVISIONS,
                updated_since=updated_since,
                bid_date_from=bid_date_from,
                page=page,
            )
        except requests.exceptions.HTTPError as e:
            log.error(f"CC API error: {e}")
            if e.response is not None:
                log.error(f"Response body: {e.response.text[:500]}")
            sys.exit(1)

        # Extract results — adjust key based on actual API response
        projects = data.get("results", data.get("data", data.get("projects", [])))

        if not projects:
            if page == 1:
                log.warning("No projects returned from CC API. Check filters and API key.")
            break

        for project in projects:
            cc_id = str(project.get("id", project.get("projectId", "unknown")))
            title = project.get("title", project.get("projectName", "?"))

            try:
                if args.dry_run:
                    # In dry-run mode, just print the raw project data
                    log.info(f"[DRY RUN] Would process: {cc_id} — {title}")
                    if args.verbose:
                        print(json.dumps(project, indent=2, default=str))
                    created += 1
                    continue

                # Check for existing lead
                existing = odoo.find_lead_by_cc_id(cc_id)

                if existing:
                    # Update existing lead
                    values = map_project_to_lead(project, odoo)
                    # Don't overwrite partner_id if already set
                    values.pop("partner_id", None)
                    odoo.write("crm.lead", [existing["id"]], values)
                    log.info(f"  ↻ Updated: [{cc_id}] {title} (lead #{existing['id']})")
                    updated += 1
                else:
                    # Create new lead
                    values = map_project_to_lead(project, odoo)
                    lead_id = odoo.create("crm.lead", values)
                    log.info(f"  ✓ Created: [{cc_id}] {title} (lead #{lead_id})")
                    created += 1

            except Exception as e:
                log.error(f"  ✗ Error processing {cc_id}: {e}")
                errors += 1

        # Pagination
        total_results = data.get("totalResults", data.get("total", 0))
        total_pages = data.get("totalPages", -1)
        if total_pages > 0 and page >= total_pages:
            break
        if len(projects) < 50:  # Last page
            break
        page += 1

    # Summary
    log.info("=" * 50)
    log.info(f"Sync complete!")
    log.info(f"  Created: {created}")
    log.info(f"  Updated: {updated}")
    log.info(f"  Skipped: {skipped}")
    log.info(f"  Errors:  {errors}")
    log.info("=" * 50)

    if errors > 0:
        sys.exit(1)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Sync ConstructConnect projects → Odoo CRM leads"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview API results without writing to Odoo",
    )
    parser.add_argument(
        "--days",
        type=int,
        default=None,
        help="Only sync projects updated in the last N days",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Print full project JSON in dry-run mode",
    )

    args = parser.parse_args()
    sync(args)


if __name__ == "__main__":
    main()
