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
    """Login to ConstructConnect with improved SSO handling"""
    print("Navigating to ConstructConnect...")
    page.goto("https://app.constructconnect.com/")
    page.wait_for_load_state("networkidle", timeout=30000)
    time.sleep(3)
    
    # Enter email on first page
    try:
        email_input = page.locator("input#email")
        email_input.wait_for(timeout=10000)
        if email_input.is_visible():
            print(f"Entering email: {CC_EMAIL}")
            email_input.fill(CC_EMAIL)
            submit_btn = page.locator("input#submitButton, button[type='submit']").first
            submit_btn.click()
            time.sleep(5)
    except Exception as e:
        print(f"Email page handling: {e}")
    
    # Wait to land on SSO page
    page.wait_for_load_state("networkidle", timeout=30000)
    print(f"Current URL: {page.url}")
    
    # Handle login.io SSO page
    if "login.io" in page.url or "constructconnect.com/login" in page.url:
        print("On SSO page, filling credentials...")
        
        # Wait for and fill email field
        try:
            email_field = page.locator("#email-input, input[name='email'], input[type='email']").first
            email_field.wait_for(timeout=10000)
            email_field.fill(CC_EMAIL)
            print("Email filled")
        except Exception as e:
            print(f"Email field: {e}")
        
        # Wait for and fill password field
        try:
            pw_field = page.locator("#password-input, input[name='password'], input[type='password']").first
            pw_field.wait_for(timeout=10000)
            pw_field.fill(CC_PASSWORD)
            print("Password filled")
        except Exception as e:
            print(f"Password field: {e}")
        
        # Click login button
        try:
            login_btn = page.locator("#login-btn, button[type='submit'], button:has-text('Sign In'), button:has-text('Log In')").first
            login_btn.click()
            print("Login button clicked, waiting for redirect...")
        except Exception as e:
            print(f"Login button: {e}")
        
        # Wait for navigation away from login page
        for i in range(30):
            time.sleep(2)
            current_url = page.url
            print(f"  Checking URL ({i+1}/30): {current_url[:60]}...")
            if "login.io" not in current_url and "login" not in current_url.split("/")[-1]:
                print("Login successful - redirected!")
                return True
            if "error" in current_url.lower() or "invalid" in page.content().lower():
                print("Login error detected")
                break
    
    # Final check
    page.wait_for_load_state("networkidle", timeout=30000)
    final_url = page.url
    print(f"Final URL: {final_url}")
    return "app.constructconnect.com" in final_url and "login" not in final_url


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
