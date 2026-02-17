#!/usr/bin/env python3
"""
Omega -> Patriot Database Replication Script
=============================================
Replicates the entire Omega Signs Co Odoo database to the Patriot Signs
Odoo.sh instance using:
  - XML-RPC to READ from Omega (Odoo Online)
  - JSON-RPC REST API to WRITE to Patriot (Odoo.sh)

Phases:
  1. Schema replication (ir.model, ir.model.fields for x_* Studio models)
  2. Access control (ir.model.access for x_* models)
  3. UI replication (ir.ui.view, ir.actions.act_window, ir.ui.menu)
  4. Data replication (in dependency order with ID mapping)

Usage:
  python omega_to_patriot_replicate.py [--phase PHASE] [--dry-run]
"""

import xmlrpc.client
import os
import sys
import json
import logging
import argparse
import urllib.request
import urllib.error
from datetime import datetime
from collections import OrderedDict

# -- Configuration -----------------------------------------------------------

OMEGA = {
    "url": os.getenv("OMEGA_URL", "https://omegasignsco.odoo.com"),
    "db": os.getenv("OMEGA_DB", "omegasignsco"),
    "login": os.getenv("OMEGA_LOGIN", "tiffany@omegasignsco.com"),
    "password": os.getenv("OMEGA_PASSWORD", "Fdlitd4m@7117"),
}

PATRIOT = {
    "url": os.getenv("PATRIOT_URL", "https://patriotsigns.odoo.com"),
    "login": os.getenv("PATRIOT_LOGIN", "tiffany@omegasignsco.com"),
    "password": os.getenv("PATRIOT_PASSWORD", "Fdlitd4m@7117"),
}

# Fields to skip during data replication (auto-generated, non-writable)
SKIP_FIELDS = {
    "id", "create_uid", "create_date", "write_uid", "write_date",
    "display_name", "__last_update",
    "message_is_follower", "message_follower_ids", "message_partner_ids",
    "message_ids", "has_message", "message_needaction", "message_needaction_counter",
    "message_has_error", "message_has_error_counter", "message_attachment_count",
    "rating_ids", "website_message_ids", "message_has_sms_error",
    "activity_ids", "activity_state", "activity_user_id", "activity_type_id",
    "activity_type_icon", "activity_date_deadline", "my_activity_date_deadline",
    "activity_summary", "activity_exception_decoration", "activity_exception_icon",
    "activity_calendar_event_id",
}

SKIP_FIELD_TYPES = {"one2many", "related", "binary"}

# -- Logging -----------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(
            f"replication_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log",
            encoding="utf-8"
        ),
    ]
)
log = logging.getLogger("replicate")

# -- Omega Connection (XML-RPC) ---------------------------------------------

class OmegaConnection:
    """XML-RPC connection to Omega (read-only source)."""
    
    def __init__(self, config):
        self.name = "OMEGA"
        self.url = config["url"]
        self.db = config["db"]
        self.login = config["login"]
        self.password = config["password"]
        self.uid = None
        self.common = xmlrpc.client.ServerProxy(f"{self.url}/xmlrpc/2/common")
        self.models = xmlrpc.client.ServerProxy(f"{self.url}/xmlrpc/2/object")
    
    def authenticate(self):
        log.info(f"[{self.name}] Authenticating as {self.login} on {self.url}")
        self.uid = self.common.authenticate(self.db, self.login, self.password, {})
        if not self.uid:
            raise Exception(f"[{self.name}] Authentication failed!")
        log.info(f"[{self.name}] Authenticated OK (uid={self.uid})")
        return self.uid
    
    def execute(self, model, method, *args, **kwargs):
        return self.models.execute_kw(
            self.db, self.uid, self.password,
            model, method, list(args), kwargs
        )
    
    def search_read(self, model, domain=None, fields=None, limit=0, offset=0, order=""):
        domain = domain or []
        kw = {}
        if fields: kw["fields"] = fields
        if limit: kw["limit"] = limit
        if offset: kw["offset"] = offset
        if order: kw["order"] = order
        return self.execute(model, "search_read", domain, **kw)
    
    def search(self, model, domain=None, limit=0, offset=0, order=""):
        domain = domain or []
        kw = {}
        if limit: kw["limit"] = limit
        if offset: kw["offset"] = offset
        if order: kw["order"] = order
        return self.execute(model, "search", domain, **kw)
    
    def read(self, model, ids, fields=None):
        kw = {}
        if fields: kw["fields"] = fields
        return self.execute(model, "read", ids, **kw)
    
    def search_count(self, model, domain=None):
        return self.execute(model, "search_count", domain or [])
    
    def fields_get(self, model, attributes=None):
        kw = {}
        if attributes: kw["attributes"] = attributes
        return self.execute(model, "fields_get", **kw)


# -- Patriot Connection (JSON-RPC / REST API) --------------------------------

class PatriotConnection:
    """JSON-RPC connection to Patriot Odoo.sh (read-write target).
    
    Uses the same approach as the working MCP server:
    session-based auth via /web/session/authenticate, then JSON-RPC calls.
    No need to know the database name.
    """
    
    def __init__(self, config):
        self.name = "PATRIOT"
        self.url = config["url"]
        self.login = config["login"]
        self.password = config["password"]
        self.uid = None
        self.session_cookie = None
        self.db = None
    
    def _jsonrpc(self, endpoint, params):
        """Low-level JSON-RPC call."""
        url = f"{self.url}{endpoint}"
        body = json.dumps({
            "jsonrpc": "2.0",
            "id": int(datetime.now().timestamp() * 1000),
            "method": "call",
            "params": params,
        }).encode("utf-8")
        
        req = urllib.request.Request(url, data=body)
        req.add_header("Content-Type", "application/json")
        if self.session_cookie:
            req.add_header("Cookie", self.session_cookie)
        
        resp = urllib.request.urlopen(req)
        
        # Capture session cookie
        for header in resp.headers.get_all("Set-Cookie") or []:
            if "session_id=" in header:
                import re
                match = re.search(r"session_id=([^;]+)", header)
                if match:
                    self.session_cookie = f"session_id={match.group(1)}"
        
        result = json.loads(resp.read().decode("utf-8"))
        if result.get("error"):
            err = result["error"]
            msg = err.get("data", {}).get("message") or err.get("message") or str(err)
            raise Exception(f"JSON-RPC error: {msg}")
        return result.get("result")
    
    def _detect_db(self):
        """Auto-detect database name."""
        if self.db:
            return self.db
        try:
            result = self._jsonrpc("/web/database/list", {})
            if isinstance(result, list) and result:
                self.db = result[0]
                log.info(f"[{self.name}] Auto-detected database: {self.db}")
                return self.db
        except Exception:
            pass
        # Fallback: derive from URL
        import re
        match = re.match(r"https?://([^.]+)\.odoo\.com", self.url)
        if match:
            self.db = match.group(1)
            return self.db
        raise Exception("Cannot determine Patriot database name")
    
    def authenticate(self):
        db = self._detect_db()
        log.info(f"[{self.name}] Authenticating as {self.login} on {self.url} (db={db})")
        result = self._jsonrpc("/web/session/authenticate", {
            "db": db,
            "login": self.login,
            "password": self.password,
        })
        if not result or not result.get("uid"):
            raise Exception(f"[{self.name}] Authentication failed!")
        self.uid = result["uid"]
        log.info(f"[{self.name}] Authenticated OK (uid={self.uid})")
        return self.uid
    
    def call_kw(self, model, method, args=None, kwargs=None):
        """Call an Odoo model method via JSON-RPC."""
        return self._jsonrpc(f"/web/dataset/call_kw/{model}/{method}", {
            "model": model,
            "method": method,
            "args": args or [],
            "kwargs": kwargs or {},
        })
    
    def search_read(self, model, domain=None, fields=None, limit=0, offset=0, order=""):
        domain = domain or []
        kw = {}
        if fields: kw["fields"] = fields
        if limit: kw["limit"] = limit
        if offset: kw["offset"] = offset
        if order: kw["order"] = order
        return self.call_kw(model, "search_read", [domain], kw)
    
    def search(self, model, domain=None, limit=0, offset=0, order=""):
        domain = domain or []
        kw = {}
        if limit: kw["limit"] = limit
        if offset: kw["offset"] = offset
        if order: kw["order"] = order
        return self.call_kw(model, "search", [domain], kw)
    
    def read(self, model, ids, fields=None):
        kw = {}
        if fields: kw["fields"] = fields
        return self.call_kw(model, "read", [ids], kw)
    
    def create(self, model, values):
        return self.call_kw(model, "create", [values])
    
    def write(self, model, ids, values):
        return self.call_kw(model, "write", [ids, values])
    
    def search_count(self, model, domain=None):
        return self.call_kw(model, "search_count", [domain or []])
    
    def fields_get(self, model, attributes=None):
        kw = {}
        if attributes: kw["attributes"] = attributes
        return self.call_kw(model, "fields_get", [], kw)


# -- ID Mapping --------------------------------------------------------------

class IDMapper:
    """Tracks old_id -> new_id mappings per model."""
    
    def __init__(self):
        self._map = {}
    
    def add(self, model, old_id, new_id):
        if model not in self._map:
            self._map[model] = {}
        self._map[model][old_id] = new_id
    
    def get(self, model, old_id):
        return self._map.get(model, {}).get(old_id)
    
    def has(self, model, old_id):
        return old_id in self._map.get(model, {})
    
    def save(self, filepath="id_mapping.json"):
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(self._map, f, indent=2)
        log.info(f"ID mapping saved to {filepath}")
    
    def load(self, filepath="id_mapping.json"):
        if os.path.exists(filepath):
            with open(filepath, "r", encoding="utf-8") as f:
                self._map = json.load(f)
                for model in self._map:
                    self._map[model] = {int(k): v for k, v in self._map[model].items()}
            total = sum(len(v) for v in self._map.values())
            log.info(f"ID mapping loaded from {filepath} ({total} entries)")
            return True
        return False
    
    def stats(self):
        return {model: len(ids) for model, ids in self._map.items()}


# -- Replication Engine -------------------------------------------------------

class Replicator:
    
    def __init__(self, source, target, dry_run=False):
        self.src = source
        self.tgt = target
        self.mapper = IDMapper()
        self.dry_run = dry_run
        self.stats = {"created": 0, "skipped": 0, "errors": 0}
    
    # -- Phase 1: Schema ---------------------------------------------------
    
    def replicate_schema(self):
        log.info("=" * 70)
        log.info("PHASE 1: Schema Replication (Studio models)")
        log.info("=" * 70)
        
        src_models = self.src.search_read(
            "ir.model",
            [["model", "=like", "x_%"], ["transient", "=", False]],
            fields=["model", "name", "info", "state", "order"],
            order="model"
        )
        log.info(f"Found {len(src_models)} x_* models in source")
        
        if self.dry_run:
            for sm in src_models:
                log.info(f"  [DRY RUN] Would create model: {sm['model']} ({sm['name']})")
                self._replicate_fields_dry(sm["model"])
            return
        
        # ---- PASS 1: Create all models WITHOUT order attribute ----
        log.info("")
        log.info("--- Pass 1: Creating model shells (no ordering) ---")
        orders_to_set = {}  # model_name -> order string
        
        for sm in src_models:
            model_name = sm["model"]
            
            existing = self.tgt.search("ir.model", [["model", "=", model_name]])
            if existing:
                log.info(f"  {model_name}: already exists (id={existing[0]})")
                self.mapper.add("ir.model", sm["id"], existing[0])
                # Still remember its order for pass 3
                if sm.get("order") and sm["order"] != "id":
                    orders_to_set[model_name] = sm["order"]
                continue
            
            try:
                new_id = self.tgt.create("ir.model", {
                    "name": sm["name"],
                    "model": model_name,
                    "state": "manual",
                    "info": sm.get("info", ""),
                    # NOTE: order="id" (default) to avoid referencing non-existent fields
                })
                log.info(f"  {model_name}: created (id={new_id})")
                self.mapper.add("ir.model", sm["id"], new_id)
                self.stats["created"] += 1
                
                # Remember the real order for pass 3
                if sm.get("order") and sm["order"] != "id":
                    orders_to_set[model_name] = sm["order"]
                    
            except Exception as e:
                log.error(f"  {model_name}: FAILED: {e}")
                self.stats["errors"] += 1
        
        # ---- PASS 2: Create all fields (with retry for forward references) ----
        log.info("")
        log.info("--- Pass 2: Creating fields ---")
        deferred_fields = []  # [(model_name, tgt_model_id, field_data)]
        
        for sm in src_models:
            model_name = sm["model"]
            tgt_model_id = self.mapper.get("ir.model", sm["id"])
            if not tgt_model_id:
                continue
            
            src_fields = self.src.search_read(
                "ir.model.fields",
                [["model", "=", model_name], ["name", "=like", "x_%"]],
                fields=[
                    "name", "field_description", "ttype", "required", "readonly",
                    "index", "store", "copied", "relation", "relation_field",
                    "size", "help", "state", "on_delete", "selection_ids",
                ]
            )
            
            existing = self.tgt.search_read(
                "ir.model.fields",
                [["model", "=", model_name], ["name", "=like", "x_%"]],
                fields=["name"]
            )
            existing_names = {f["name"] for f in existing}
            
            for f in src_fields:
                fname = f["name"]
                if fname in existing_names:
                    self.stats["skipped"] += 1
                    continue
                
                success = self._create_field(model_name, tgt_model_id, f)
                if not success:
                    deferred_fields.append((model_name, tgt_model_id, f))
        
        # Retry deferred fields (forward references should now exist)
        if deferred_fields:
            log.info(f"")
            log.info(f"--- Pass 2b: Retrying {len(deferred_fields)} deferred fields ---")
            still_failed = []
            for model_name, tgt_model_id, f in deferred_fields:
                success = self._create_field(model_name, tgt_model_id, f, retry=True)
                if not success:
                    still_failed.append((model_name, f["name"], f["ttype"]))
            
            if still_failed:
                log.warning(f"  {len(still_failed)} fields still failed after retry:")
                for mn, fn, ft in still_failed[:20]:
                    log.warning(f"    {mn}.{fn} ({ft})")
        
        # ---- PASS 3: Update model ordering now that fields exist ----
        if orders_to_set:
            log.info("")
            log.info(f"--- Pass 3: Setting model ordering ({len(orders_to_set)} models) ---")
            for model_name, order_str in orders_to_set.items():
                tgt_model_ids = self.tgt.search("ir.model", [["model", "=", model_name]])
                if not tgt_model_ids:
                    continue
                try:
                    self.tgt.write("ir.model", tgt_model_ids, {"order": order_str})
                    log.info(f"  {model_name}: order = '{order_str}'")
                except Exception as e:
                    log.warning(f"  {model_name}: failed to set order: {e}")
    
    def _create_field(self, model_name, tgt_model_id, f, retry=False):
        """Create a single field on the target. Returns True on success."""
        fname = f["name"]
        try:
            vals = {
                "model_id": tgt_model_id,
                "name": fname,
                "field_description": f["field_description"],
                "ttype": f["ttype"],
                "required": f.get("required", False),
                "readonly": f.get("readonly", False),
                "index": f.get("index", False),
                "store": f.get("store", True),
                "copied": f.get("copied", True),
                "state": "manual",
                "help": f.get("help", ""),
            }
            
            # Handle relational fields
            if f["ttype"] in ("many2one", "one2many", "many2many"):
                if f.get("relation"):
                    vals["relation"] = f["relation"]
                if f.get("relation_field"):
                    vals["relation_field"] = f["relation_field"]
                # Fix ondelete for required m2o fields
                if f["ttype"] == "many2one" and f.get("required"):
                    on_delete = f.get("on_delete", "cascade")
                    if on_delete == "set null":
                        vals["on_delete"] = "cascade"
                    else:
                        vals["on_delete"] = on_delete
            
            # Handle selection fields - fetch selection options from source
            if f["ttype"] == "selection" and f.get("selection_ids"):
                sel_data = self.src.read("ir.model.fields.selection",
                    f["selection_ids"], ["value", "name", "sequence"])
                vals["selection_ids"] = [
                    (0, 0, {"value": s["value"], "name": s["name"], "sequence": s.get("sequence", 0)})
                    for s in sel_data
                ]
            
            new_id = self.tgt.create("ir.model.fields", vals)
            prefix = "  (retry)" if retry else ""
            log.info(f"      Created field{prefix} {model_name}.{fname} ({f['ttype']})")
            self.stats["created"] += 1
            return True
        except Exception as e:
            if not retry:
                # Silently defer on first attempt for missing model refs
                if "Unknown model name" in str(e) or "ondelete" in str(e):
                    return False
            log.warning(f"      FAILED field {model_name}.{fname}: {e}")
            self.stats["errors"] += 1
            return False
    
    def _replicate_fields_dry(self, model_name):
        src_fields = self.src.search_read(
            "ir.model.fields",
            [["model", "=", model_name], ["name", "=like", "x_%"]],
            fields=["name", "ttype"]
        )
        for f in src_fields:
            log.info(f"      [DRY RUN] field: {f['name']} ({f['ttype']})")
    
    # -- Phase 2: Access Control -------------------------------------------
    
    def replicate_access(self):
        log.info("")
        log.info("=" * 70)
        log.info("PHASE 2: Access Control")
        log.info("=" * 70)
        
        src_access = self.src.search_read(
            "ir.model.access",
            [["model_id.model", "=like", "x_%"]],
            fields=[
                "name", "model_id", "group_id",
                "perm_read", "perm_write", "perm_create", "perm_unlink"
            ]
        )
        log.info(f"Found {len(src_access)} access rules")
        
        for rule in src_access:
            model_id_val = rule["model_id"]
            src_model_id = model_id_val[0] if isinstance(model_id_val, (list, tuple)) else model_id_val
            
            tgt_model_id = self.mapper.get("ir.model", src_model_id)
            if not tgt_model_id:
                log.warning(f"  No mapping for model_id {src_model_id}, skipping")
                continue
            
            existing = self.tgt.search("ir.model.access", [
                ["name", "=", rule["name"]],
                ["model_id", "=", tgt_model_id],
            ])
            if existing:
                self.stats["skipped"] += 1
                continue
            
            if self.dry_run:
                log.info(f"  [DRY RUN] access rule: {rule['name']}")
                continue
            
            try:
                vals = {
                    "name": rule["name"],
                    "model_id": tgt_model_id,
                    "perm_read": rule["perm_read"],
                    "perm_write": rule["perm_write"],
                    "perm_create": rule["perm_create"],
                    "perm_unlink": rule["perm_unlink"],
                }
                if rule.get("group_id") and isinstance(rule["group_id"], (list, tuple)):
                    group_name = rule["group_id"][1]
                    tgt_groups = self.tgt.search("res.groups", [["name", "=", group_name]], limit=1)
                    if tgt_groups:
                        vals["group_id"] = tgt_groups[0]
                
                new_id = self.tgt.create("ir.model.access", vals)
                log.info(f"  Created: {rule['name']} (id={new_id})")
                self.stats["created"] += 1
            except Exception as e:
                log.warning(f"  FAILED: {rule['name']}: {e}")
                self.stats["errors"] += 1
    
    # -- Phase 3: UI -------------------------------------------------------
    
    def replicate_ui(self):
        log.info("")
        log.info("=" * 70)
        log.info("PHASE 3: UI Replication")
        log.info("=" * 70)
        self._replicate_views()
        self._replicate_actions()
    
    def _replicate_views(self):
        log.info("--- Views ---")
        src_views = self.src.search_read(
            "ir.ui.view",
            [["model", "=like", "x_%"]],
            fields=["name", "model", "type", "arch_db", "priority", "active"],
            order="priority"
        )
        log.info(f"Found {len(src_views)} views")
        
        for v in src_views:
            existing = self.tgt.search("ir.ui.view", [
                ["name", "=", v["name"]],
                ["model", "=", v["model"]],
                ["type", "=", v["type"]],
            ])
            if existing:
                self.mapper.add("ir.ui.view", v["id"], existing[0])
                self.stats["skipped"] += 1
                continue
            
            if self.dry_run:
                log.info(f"  [DRY RUN] view: {v['name']} ({v['type']} for {v['model']})")
                continue
            
            try:
                new_id = self.tgt.create("ir.ui.view", {
                    "name": v["name"],
                    "model": v["model"],
                    "type": v["type"],
                    "arch_db": v["arch_db"],
                    "priority": v.get("priority", 16),
                    "active": v.get("active", True),
                })
                log.info(f"  Created: {v['name']} ({v['type']}) id={new_id}")
                self.mapper.add("ir.ui.view", v["id"], new_id)
                self.stats["created"] += 1
            except Exception as e:
                log.warning(f"  FAILED view {v['name']}: {e}")
                self.stats["errors"] += 1
    
    def _replicate_actions(self):
        log.info("--- Window Actions ---")
        src_actions = self.src.search_read(
            "ir.actions.act_window",
            [["res_model", "=like", "x_%"]],
            fields=["name", "res_model", "view_mode", "domain", "context",
                     "target", "limit", "help", "type"],
        )
        log.info(f"Found {len(src_actions)} actions")
        
        for a in src_actions:
            existing = self.tgt.search("ir.actions.act_window", [
                ["name", "=", a["name"]],
                ["res_model", "=", a["res_model"]],
            ])
            if existing:
                self.mapper.add("ir.actions.act_window", a["id"], existing[0])
                self.stats["skipped"] += 1
                continue
            
            if self.dry_run:
                log.info(f"  [DRY RUN] action: {a['name']} -> {a['res_model']}")
                continue
            
            try:
                vals = {
                    "name": a["name"],
                    "res_model": a["res_model"],
                    "view_mode": a.get("view_mode", "list,form"),
                    "target": a.get("target", "current"),
                    "type": "ir.actions.act_window",
                }
                if a.get("domain"): vals["domain"] = a["domain"]
                if a.get("context"): vals["context"] = a["context"]
                if a.get("help"): vals["help"] = a["help"]
                if a.get("limit"): vals["limit"] = a["limit"]
                
                new_id = self.tgt.create("ir.actions.act_window", vals)
                log.info(f"  Created: {a['name']} id={new_id}")
                self.mapper.add("ir.actions.act_window", a["id"], new_id)
                self.stats["created"] += 1
            except Exception as e:
                log.warning(f"  FAILED action {a['name']}: {e}")
                self.stats["errors"] += 1
    
    # -- Phase 4: Data -----------------------------------------------------
    
    def replicate_data(self):
        log.info("")
        log.info("=" * 70)
        log.info("PHASE 4: Data Replication")
        log.info("=" * 70)
        
        plan = OrderedDict([
            ("res.partner", {
                "domain": [["id", ">", 1]],
                "key_fields": ["name", "email"],
                "fields_exclude": {"image_1920", "image_1024", "image_512",
                                   "image_256", "image_128", "avatar_1920",
                                   "avatar_1024", "avatar_512", "avatar_256", "avatar_128"},
            }),
            ("product.category", {"domain": [], "key_fields": ["name"]}),
            ("uom.uom", {"domain": [], "key_fields": ["name"]}),
            ("product.template", {
                "domain": [],
                "key_fields": ["name"],
                "fields_exclude": {"image_1920", "image_1024", "image_512",
                                   "image_256", "image_128"},
            }),
            ("product.product", {
                "domain": [],
                "key_fields": ["default_code", "name"],
                "fields_exclude": {"image_1920", "image_1024", "image_512",
                                   "image_256", "image_128"},
            }),
            ("crm.stage", {"domain": [], "key_fields": ["name"]}),
            ("crm.lead", {
                "domain": [],
                "relational_mappings": {
                    "partner_id": "res.partner",
                    "stage_id": "crm.stage",
                },
            }),
            ("x_sign_categories", {"domain": [], "key_fields": ["x_name"]}),
            ("x_sign_sub_types", {
                "domain": [],
                "key_fields": ["x_name"],
            }),
            ("x_sign_types", {
                "domain": [],
                "key_fields": ["x_name"],
                "relational_mappings": {
                    "x_studio_project": "crm.lead",
                    "x_studio_sign_subtype": "x_sign_sub_types",
                    "x_studio_supplier": "res.partner",
                },
            }),
            ("x_sign_schedule", {
                "domain": [],
                "key_fields": ["x_name"],
                "relational_mappings": {
                    "x_studio_opportunity_bid": "crm.lead",
                },
            }),
            ("sale.order", {
                "domain": [],
                "key_fields": ["name"],
                "relational_mappings": {
                    "partner_id": "res.partner",
                    "opportunity_id": "crm.lead",
                },
            }),
            ("sale.order.line", {
                "domain": [],
                "relational_mappings": {
                    "order_id": "sale.order",
                    "product_id": "product.product",
                },
            }),
            ("project.project", {
                "domain": [],
                "key_fields": ["name"],
                "relational_mappings": {
                    "partner_id": "res.partner",
                },
            }),
            ("project.task", {
                "domain": [],
                "key_fields": ["name"],
                "relational_mappings": {
                    "project_id": "project.project",
                    "partner_id": "res.partner",
                },
            }),
        ])
        
        for model_name, config in plan.items():
            self._replicate_model_data(model_name, config)
            self.mapper.save()
    
    def _replicate_model_data(self, model_name, config):
        domain = config.get("domain", [])
        key_fields = config.get("key_fields", [])
        relational_mappings = config.get("relational_mappings", {})
        fields_exclude = config.get("fields_exclude", set())
        
        log.info(f"")
        log.info(f"--- {model_name} ---")
        
        try:
            src_fdefs = self.src.fields_get(model_name,
                attributes=["type", "readonly", "required", "relation"])
        except Exception as e:
            log.error(f"  Cannot get fields: {e}")
            return
        
        writable = []
        for fname, fdef in src_fdefs.items():
            if fname in SKIP_FIELDS or fname in fields_exclude:
                continue
            if fdef.get("type") in SKIP_FIELD_TYPES:
                continue
            if fdef.get("readonly") and fname not in ("x_name", "name"):
                continue
            writable.append(fname)
        
        src_count = self.src.search_count(model_name, domain)
        log.info(f"  Source: {src_count} records, {len(writable)} writable fields")
        
        if src_count == 0:
            return
        
        batch_size = 100
        offset = 0
        created = skipped = errors = 0
        
        while offset < src_count:
            records = self.src.search_read(
                model_name, domain,
                fields=writable + ["id"],
                limit=batch_size, offset=offset, order="id"
            )
            if not records:
                break
            
            for rec in records:
                old_id = rec["id"]
                
                if self.mapper.has(model_name, old_id):
                    skipped += 1
                    continue
                
                existing_id = self._find_existing(model_name, rec, key_fields)
                if existing_id:
                    self.mapper.add(model_name, old_id, existing_id)
                    skipped += 1
                    continue
                
                vals = self._prepare_values(rec, src_fdefs, relational_mappings)
                
                if self.dry_run:
                    display = rec.get("name") or rec.get("x_name") or str(old_id)
                    log.info(f"  [DRY RUN] {display}")
                    continue
                
                try:
                    new_id = self.tgt.create(model_name, vals)
                    self.mapper.add(model_name, old_id, new_id)
                    created += 1
                    if created % 50 == 0:
                        log.info(f"  Progress: {created} created, {skipped} skipped")
                except Exception as e:
                    display = rec.get("name") or rec.get("x_name") or str(old_id)
                    log.warning(f"  FAILED '{display}': {e}")
                    errors += 1
            
            offset += batch_size
        
        log.info(f"  Result: {created} created, {skipped} skipped, {errors} errors")
        self.stats["created"] += created
        self.stats["skipped"] += skipped
        self.stats["errors"] += errors
    
    def _find_existing(self, model_name, record, key_fields):
        if not key_fields:
            return None
        domain = []
        for kf in key_fields:
            val = record.get(kf)
            if val:
                domain.append([kf, "=", val])
        if not domain:
            return None
        try:
            existing = self.tgt.search(model_name, domain, limit=1)
            return existing[0] if existing else None
        except:
            return None
    
    def _prepare_values(self, record, field_defs, relational_mappings):
        vals = {}
        for fname, value in record.items():
            if fname == "id" or fname in SKIP_FIELDS:
                continue
            if value is False or value is None:
                continue
            
            fdef = field_defs.get(fname, {})
            ftype = fdef.get("type", "")
            
            if ftype == "many2one" and isinstance(value, (list, tuple)):
                old_rel_id = value[0]
                relation = fdef.get("relation", "")
                
                if fname in relational_mappings:
                    new_id = self.mapper.get(relational_mappings[fname], old_rel_id)
                    if new_id:
                        vals[fname] = new_id
                elif relation:
                    try:
                        tgt = self.tgt.search(relation, [["id", "=", old_rel_id]], limit=1)
                        if tgt:
                            vals[fname] = tgt[0]
                    except:
                        pass
            
            elif ftype == "many2many" and isinstance(value, list):
                relation = fdef.get("relation", "")
                if relation and value:
                    mapped = []
                    for oid in value:
                        nid = self.mapper.get(relation, oid)
                        if nid:
                            mapped.append(nid)
                        else:
                            try:
                                t = self.tgt.search(relation, [["id", "=", oid]], limit=1)
                                if t:
                                    mapped.append(t[0])
                            except:
                                pass
                    if mapped:
                        vals[fname] = [(6, 0, mapped)]
            else:
                vals[fname] = value
        
        return vals
    
    # -- Verify ------------------------------------------------------------
    
    def verify(self):
        log.info("")
        log.info("=" * 70)
        log.info("VERIFICATION")
        log.info("=" * 70)
        
        models = [
            "res.partner", "crm.lead", "sale.order", "product.product",
            "project.project",
            "x_sign_types", "x_sign_schedule", "x_sign_sub_types", "x_sign_categories",
        ]
        
        for model in models:
            try:
                sc = self.src.search_count(model)
                tc = self.tgt.search_count(model)
                ok = "OK" if tc >= sc else "MISMATCH"
                log.info(f"  {ok}: {model} source={sc} target={tc}")
            except Exception as e:
                log.warning(f"  ERROR: {model}: {e}")


# -- Main --------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Replicate Omega -> Patriot")
    parser.add_argument("--phase", type=int, choices=[1, 2, 3, 4])
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--verify-only", action="store_true")
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()
    
    log.info("=" * 70)
    log.info("OMEGA -> PATRIOT DATABASE REPLICATION")
    log.info(f"Started: {datetime.now().isoformat()}")
    log.info(f"Mode: {'DRY RUN' if args.dry_run else 'LIVE'}")
    log.info("=" * 70)
    
    omega = OmegaConnection(OMEGA)
    patriot = PatriotConnection(PATRIOT)
    
    omega.authenticate()
    patriot.authenticate()
    
    replicator = Replicator(omega, patriot, dry_run=args.dry_run)
    
    if args.resume:
        replicator.mapper.load()
    
    if args.verify_only:
        replicator.verify()
        return
    
    if args.phase is None or args.phase == 1:
        replicator.replicate_schema()
    if args.phase is None or args.phase == 2:
        replicator.replicate_access()
    if args.phase is None or args.phase == 3:
        replicator.replicate_ui()
    if args.phase is None or args.phase == 4:
        replicator.replicate_data()
    
    replicator.mapper.save()
    replicator.verify()
    
    log.info("")
    log.info("=" * 70)
    log.info("SUMMARY")
    log.info("=" * 70)
    log.info(f"  Created: {replicator.stats['created']}")
    log.info(f"  Skipped: {replicator.stats['skipped']}")
    log.info(f"  Errors:  {replicator.stats['errors']}")
    log.info(f"  Mappings: {replicator.mapper.stats()}")
    log.info(f"Completed: {datetime.now().isoformat()}")


if __name__ == "__main__":
    main()
