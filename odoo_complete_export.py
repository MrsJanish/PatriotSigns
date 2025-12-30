"""
Complete Odoo Database Export Script
=====================================
Exports ALL data from an Odoo instance via XML-RPC API for complete database reconstruction.

Features:
- Exports all models (base + custom), even empty ones
- Includes fields, views, modules, actions, menus, security rules
- Skips models already exported (configurable)
- Handles large datasets with pagination
- Comprehensive logging and error handling

Usage:
    python odoo_complete_export.py

Configuration:
    Set environment variables or edit the CONFIG section below.
"""

import xmlrpc.client
import csv
import os
import sys
import logging
from datetime import datetime
from pathlib import Path
from getpass import getpass
from typing import List, Dict, Any, Optional

# =============================================================================
# CONFIGURATION
# =============================================================================

CONFIG = {
    # Odoo Connection
    "url": "https://omegasignsco.odoo.com",
    "db": "omegasignsco",
    "username": "tiffany@omegasignsco.com",
    "password": "Fdlitd4m@7117",
    
    # Export Settings
    "existing_export_dir": r"C:\Users\darre\OneDrive\Desktop\PatriotSigns\Odoo_Data_Export",
    "output_dir": r"C:\Users\darre\OneDrive\Desktop\PatriotSigns\Odoo_Data_Export_Complete",
    "skip_existing": True,  # Skip models already exported
    "export_empty_models": True,  # Export headers for empty models
    "batch_size": 1000,  # Records per batch for large models
    
    # Models to skip (very large or binary-heavy)
    "skip_models": [
        # Uncomment to skip large models:
        # "mail.message",  # Can be 300+ MB
        # "ir.attachment",  # Contains binary files
    ],
    
    # Priority models to export first (technical models for reconstruction)
    "priority_models": [
        "ir.module.module",
        "ir.module.module.dependency",
        "ir.model",
        "ir.model.fields",
        "ir.model.fields.selection",
        "ir.model.constraint",
        "ir.model.relation",
        "ir.model.access",
        "ir.model.data",
        "ir.rule",
        "ir.ui.view",
        "ir.ui.menu",
        "ir.actions.act_window",
        "ir.actions.act_window.view",
        "ir.actions.server",
        "ir.actions.client",
        "ir.actions.report",
        "ir.sequence",
        "ir.cron",
        "ir.filters",
        "ir.default",
        "base.automation",
        "res.groups",
        "res.users",
        "res.company",
    ],
}

# =============================================================================
# LOGGING SETUP
# =============================================================================

def setup_logging(output_dir: str) -> logging.Logger:
    """Configure logging to both file and console."""
    log_dir = Path(output_dir)
    log_dir.mkdir(parents=True, exist_ok=True)
    
    log_file = log_dir / f"export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.FileHandler(log_file, encoding="utf-8"),
            logging.StreamHandler(sys.stdout)
        ]
    )
    return logging.getLogger(__name__)

# =============================================================================
# ODOO CONNECTION
# =============================================================================

class OdooConnection:
    """Handles XML-RPC connection to Odoo."""
    
    def __init__(self, url: str, db: str, username: str, password: str):
        self.url = url.rstrip("/")
        self.db = db
        self.username = username
        self.password = password
        self.uid = None
        self.common = None
        self.models = None
        
    def connect(self) -> bool:
        """Establish connection and authenticate."""
        try:
            # Common endpoint for authentication
            self.common = xmlrpc.client.ServerProxy(f"{self.url}/xmlrpc/2/common")
            
            # Test connection
            version = self.common.version()
            logging.info(f"Connected to Odoo {version.get('server_version', 'unknown')}")
            
            # Authenticate
            self.uid = self.common.authenticate(self.db, self.username, self.password, {})
            if not self.uid:
                logging.error("Authentication failed. Check credentials.")
                return False
            
            logging.info(f"Authenticated as user ID: {self.uid}")
            
            # Models endpoint for data operations
            self.models = xmlrpc.client.ServerProxy(f"{self.url}/xmlrpc/2/object")
            
            return True
            
        except Exception as e:
            logging.error(f"Connection failed: {e}")
            return False
    
    def execute(self, model: str, method: str, *args, **kwargs) -> Any:
        """Execute a method on an Odoo model."""
        return self.models.execute_kw(
            self.db, self.uid, self.password,
            model, method, list(args), kwargs
        )
    
    def search_read(self, model: str, domain: List = None, fields: List = None, 
                    offset: int = 0, limit: int = None) -> List[Dict]:
        """Search and read records from a model."""
        domain = domain or []
        options = {"offset": offset}
        if fields:
            options["fields"] = fields
        if limit:
            options["limit"] = limit
        
        return self.execute(model, "search_read", domain, **options)
    
    def search_count(self, model: str, domain: List = None) -> int:
        """Count records matching a domain."""
        return self.execute(model, "search_count", domain or [])
    
    def fields_get(self, model: str) -> Dict:
        """Get field definitions for a model."""
        return self.execute(model, "fields_get", [], {"attributes": ["string", "type", "relation"]})

# =============================================================================
# EXPORT FUNCTIONS
# =============================================================================

def get_all_models(conn: OdooConnection) -> List[Dict]:
    """Get list of all models in the database."""
    logging.info("Fetching all model definitions...")
    models = conn.search_read(
        "ir.model",
        [],
        ["model", "name", "state", "transient"]
    )
    logging.info(f"Found {len(models)} models")
    return models

def get_existing_exports(export_dir: str) -> set:
    """Get set of model names already exported."""
    existing = set()
    export_path = Path(export_dir)
    if export_path.exists():
        for csv_file in export_path.glob("*.csv"):
            # Convert filename back to model name
            model_name = csv_file.stem.replace(".", ".")
            existing.add(model_name)
    logging.info(f"Found {len(existing)} existing exports")
    return existing

def sanitize_value(value: Any) -> str:
    """Convert a value to a safe CSV string."""
    if value is None or value is False:
        return ""
    if isinstance(value, (list, tuple)):
        # Handle Many2many/One2many as comma-separated IDs or representations
        if value and isinstance(value[0], (int, float)):
            return str(value)
        return str(value)
    if isinstance(value, bytes):
        return "<binary data>"
    return str(value)

def export_model(conn: OdooConnection, model_name: str, output_dir: str, 
                 batch_size: int = 1000) -> Dict:
    """Export all records from a model to CSV."""
    result = {
        "model": model_name,
        "success": False,
        "record_count": 0,
        "error": None
    }
    
    try:
        # Get field definitions
        fields_info = conn.fields_get(model_name)
        field_names = list(fields_info.keys())
        
        if not field_names:
            logging.warning(f"No fields found for {model_name}")
            result["error"] = "No fields"
            return result
        
        # Count total records
        total_records = conn.search_count(model_name)
        result["record_count"] = total_records
        
        # Prepare output file
        output_path = Path(output_dir) / f"{model_name}.csv"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=field_names, extrasaction="ignore")
            writer.writeheader()
            
            if total_records == 0:
                logging.info(f"  {model_name}: 0 records (headers only)")
            else:
                # Export in batches
                offset = 0
                while offset < total_records:
                    records = conn.search_read(
                        model_name, [], field_names, 
                        offset=offset, limit=batch_size
                    )
                    
                    for record in records:
                        # Sanitize all values
                        clean_record = {k: sanitize_value(v) for k, v in record.items()}
                        writer.writerow(clean_record)
                    
                    offset += len(records)
                    if total_records > batch_size:
                        logging.info(f"  {model_name}: {offset}/{total_records} records")
                
                logging.info(f"  {model_name}: {total_records} records exported")
        
        result["success"] = True
        
    except Exception as e:
        result["error"] = str(e)
        logging.error(f"  {model_name}: ERROR - {e}")
    
    return result

def run_export(config: Dict) -> Dict:
    """Run the complete export process."""
    logger = setup_logging(config["output_dir"])
    
    # Prompt for missing credentials
    url = config["url"]
    db = config["db"] or input("Enter Odoo database name: ").strip()
    username = config["username"] or input("Enter Odoo username (email): ").strip()
    password = config["password"] or getpass("Enter Odoo API key or password: ")
    
    logging.info("=" * 60)
    logging.info("ODOO COMPLETE DATABASE EXPORT")
    logging.info("=" * 60)
    logging.info(f"URL: {url}")
    logging.info(f"Database: {db}")
    logging.info(f"Output: {config['output_dir']}")
    
    # Connect to Odoo
    conn = OdooConnection(url, db, username, password)
    if not conn.connect():
        return {"success": False, "error": "Connection failed"}
    
    # Get all models
    all_models = get_all_models(conn)
    model_names = [m["model"] for m in all_models]
    
    # Get existing exports
    existing = set()
    if config["skip_existing"]:
        existing = get_existing_exports(config["existing_export_dir"])
    
    # Build export queue
    export_queue = []
    
    # Add priority models first
    for model in config["priority_models"]:
        if model in model_names and model not in config["skip_models"]:
            if not config["skip_existing"] or model not in existing:
                export_queue.append(model)
    
    # Add remaining models
    for model in model_names:
        if model not in export_queue and model not in config["skip_models"]:
            if not config["skip_existing"] or model not in existing:
                export_queue.append(model)
    
    logging.info(f"Models to export: {len(export_queue)}")
    logging.info(f"Models skipped (existing): {len(existing)}")
    logging.info(f"Models skipped (config): {len(config['skip_models'])}")
    
    # Export each model
    results = {
        "success": 0,
        "failed": 0,
        "empty": 0,
        "errors": []
    }
    
    for i, model_name in enumerate(export_queue, 1):
        logging.info(f"[{i}/{len(export_queue)}] Exporting {model_name}...")
        
        result = export_model(conn, model_name, config["output_dir"], config["batch_size"])
        
        if result["success"]:
            results["success"] += 1
            if result["record_count"] == 0:
                results["empty"] += 1
        else:
            results["failed"] += 1
            results["errors"].append(result)
    
    # Summary
    logging.info("=" * 60)
    logging.info("EXPORT COMPLETE")
    logging.info("=" * 60)
    logging.info(f"Successful: {results['success']}")
    logging.info(f"  - With data: {results['success'] - results['empty']}")
    logging.info(f"  - Empty (headers only): {results['empty']}")
    logging.info(f"Failed: {results['failed']}")
    
    if results["errors"]:
        logging.info("Errors:")
        for err in results["errors"]:
            logging.info(f"  - {err['model']}: {err['error']}")
    
    return results

# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("ODOO COMPLETE DATABASE EXPORT")
    print("=" * 60 + "\n")
    
    # Check if credentials are set
    if not CONFIG["db"]:
        print("No database configured. You will be prompted for credentials.\n")
        print("TIP: Set environment variables to avoid prompts:")
        print("  ODOO_URL=https://your-odoo.com")
        print("  ODOO_DB=your_database")
        print("  ODOO_USER=your@email.com")
        print("  ODOO_PASSWORD=your_api_key")
        print()
    
    try:
        results = run_export(CONFIG)
        print("\nExport finished. Check the log file for details.")
    except KeyboardInterrupt:
        print("\nExport cancelled by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\nFatal error: {e}")
        sys.exit(1)
