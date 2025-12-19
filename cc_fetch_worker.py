#!/usr/bin/env python3
"""
CC Fetch Worker for GitHub Actions
Fetches documents from ConstructConnect and uploads to Odoo
"""

import sys
import os
import time
import base64
import zipfile
import tempfile
import xmlrpc.client
from pathlib import Path
from playwright.sync_api import sync_playwright

# Get credentials from environment
CC_EMAIL = os.environ.get("CC_EMAIL")
CC_PASSWORD = os.environ.get("CC_PASSWORD")
ODOO_URL = os.environ.get("ODOO_URL")
ODOO_DB = os.environ.get("ODOO_DB")
ODOO_USER = os.environ.get("ODOO_USER")
ODOO_PASSWORD = os.environ.get("ODOO_PASSWORD")


def login_to_cc(page, context):
    """Login to ConstructConnect"""
    print("Navigating to ConstructConnect...")
    page.goto("https://app.constructconnect.com/")
    time.sleep(3)
    
    # Enter email on first page
    email_input = page.locator("input#email")
    if email_input.is_visible():
        email_input.fill(CC_EMAIL)
        page.locator("input#submitButton").click()
        time.sleep(3)
    
    # Handle login.io SSO page
    if "login.io.constructconnect.com" in page.url:
        print("On SSO page, filling credentials...")
        page.locator("#email-input").fill(CC_EMAIL)
        page.locator("#password-input").fill(CC_PASSWORD)
        page.locator("#login-btn").click()
        time.sleep(5)
    
    # Wait for redirect
    page.wait_for_load_state("networkidle", timeout=30000)
    print(f"Login complete, URL: {page.url}")
    return "login" not in page.url.lower()


def fetch_documents(page, context, project_id, download_dir):
    """Navigate to project and download documents"""
    print(f"Fetching documents for project {project_id}...")
    
    # Navigate to project
    project_url = f"https://app.constructconnect.com/project/{project_id}"
    page.goto(project_url, timeout=60000)
    page.wait_for_load_state("networkidle", timeout=30000)
    time.sleep(5)
    
    # Click "View/Download Documents" button
    docs_btn = page.locator("button:has-text('View/Download Documents')")
    if docs_btn.is_visible():
        print("Opening documents tab...")
        
        # This opens a new tab
        with context.expect_page() as new_page_info:
            docs_btn.click()
        
        docs_page = new_page_info.value
        docs_page.wait_for_load_state("networkidle", timeout=60000)
        time.sleep(10)
        
        # Click Select All
        select_all = docs_page.locator("button:has-text('Select All')")
        if select_all.is_visible():
            select_all.click()
            time.sleep(2)
        
        # Click Download All
        download_btn = docs_page.locator("button:has-text('Download All')")
        if download_btn.is_visible():
            print("Downloading all documents...")
            with docs_page.expect_download(timeout=300000) as download_info:
                download_btn.click()
            
            download = download_info.value
            download_path = os.path.join(download_dir, "documents.zip")
            download.save_as(download_path)
            print(f"Downloaded to {download_path}")
            return download_path
    
    print("No documents button found")
    return None


def upload_to_odoo(opportunity_id, zip_path):
    """Upload documents to Odoo"""
    print(f"Uploading documents to Odoo opportunity {opportunity_id}...")
    
    # Connect to Odoo
    common = xmlrpc.client.ServerProxy(f"{ODOO_URL}/xmlrpc/2/common")
    uid = common.authenticate(ODOO_DB, ODOO_USER, ODOO_PASSWORD, {})
    
    if not uid:
        print("Failed to authenticate with Odoo")
        return False
    
    models = xmlrpc.client.ServerProxy(f"{ODOO_URL}/xmlrpc/2/object")
    
    # Extract and upload each file
    with tempfile.TemporaryDirectory() as extract_dir:
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(extract_dir)
        
        for root, dirs, files in os.walk(extract_dir):
            for filename in files:
                filepath = os.path.join(root, filename)
                with open(filepath, 'rb') as f:
                    file_data = base64.b64encode(f.read()).decode('utf-8')
                
                # Create attachment
                attachment_id = models.execute_kw(
                    ODOO_DB, uid, ODOO_PASSWORD,
                    'ir.attachment', 'create',
                    [{
                        'name': filename,
                        'datas': file_data,
                        'res_model': 'cc.opportunity',
                        'res_id': int(opportunity_id),
                    }]
                )
                print(f"Uploaded {filename} as attachment {attachment_id}")
    
    # Update opportunity status
    models.execute_kw(
        ODOO_DB, uid, ODOO_PASSWORD,
        'cc.opportunity', 'write',
        [[int(opportunity_id)], {'state': 'ready'}]
    )
    print("Set opportunity state to 'ready'")
    return True


def main():
    if len(sys.argv) < 3:
        print("Usage: python cc_fetch_worker.py <project_id> <opportunity_id>")
        sys.exit(1)
    
    project_id = sys.argv[1]
    opportunity_id = sys.argv[2]
    
    print(f"Starting fetch for CC Project {project_id}, Odoo Opportunity {opportunity_id}")
    
    with tempfile.TemporaryDirectory() as download_dir:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(accept_downloads=True)
            page = context.new_page()
            
            # Login
            if not login_to_cc(page, context):
                print("Login failed!")
                sys.exit(1)
            
            # Fetch documents
            zip_path = fetch_documents(page, context, project_id, download_dir)
            
            browser.close()
        
        if zip_path and os.path.exists(zip_path):
            # Upload to Odoo
            upload_to_odoo(opportunity_id, zip_path)
            print("Done!")
        else:
            print("No documents downloaded")


if __name__ == "__main__":
    main()
