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
            
            # Take screenshot for debugging
            time.sleep(3)
            page.screenshot(path="debug_after_login_click.png")
            print("Saved debug screenshot: debug_after_login_click.png")
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
            if "error" in current_url.lower():
                print("Login error detected in URL")
                break
    
    # Final check
    page.wait_for_load_state("networkidle", timeout=30000)
    final_url = page.url
    print(f"Final URL: {final_url}")
    return "app.constructconnect.com" in final_url and "login" not in final_url


def fetch_documents(page, context, project_id, download_dir, source_url=None):
    """Navigate to project and download documents"""
    print(f"Fetching documents for project {project_id}...")
    
    # Wait on dashboard/search page first to avoid "Uh oh" error
    print("Waiting for dashboard to settle...")
    time.sleep(10)
    
    # Navigate to project - use source_url if provided, otherwise construct
    if source_url and source_url.startswith('http'):
        project_url = source_url
    else:
        project_url = f"https://app.constructconnect.com/project/{project_id}"
    
    print(f"Navigating to {project_url}")
    page.goto(project_url, timeout=120000)
    
    # Wait for initial load
    try:
        page.wait_for_load_state("domcontentloaded", timeout=60000)
    except Exception as e:
        print(f"Load state wait: {e}")

    print("Waiting for Page/React content to load...")
    time.sleep(15)
    
    # Check for "Uh oh" error immediately
    retry_search = False
    try:
        body_text = page.locator("body").inner_text()
        if "Uh oh, something happened" in body_text:
            print("Detected 'Uh oh' error page. Will retry via Search...")
            retry_search = True
        elif "Try Again" in body_text:
             print("Detected 'Try Again' text. Will retry via Search...")
             retry_search = True
    except:
        pass

    # Selectors for the "Documents" tab or button
    doc_tab_selectors = [
        "button:has-text('View/Download Documents')",
        "a:has-text('View/Download Documents')",
        "button:has-text('Documents')",
        "a:has-text('Documents')",
        "#tab-documents",
        "[aria-label='Documents']",
        "li:has-text('Documents')"
    ]
    
    docs_btn = None
    if not retry_search:
        for selector in doc_tab_selectors:
            try:
                print(f"Checking for documents tab: {selector}")
                btn = page.locator(selector).first
                if btn.is_visible(timeout=2000):
                    docs_btn = btn
                    print(f"Found documents button: {selector}")
                    break
            except:
                continue
    
    # If no doc button found (or error page detected), try Global Search Fallback
    if not docs_btn or retry_search:
        print("Direct navigation failed or documents not found. Implementing Global Search Fallback...")
        
        try:
            # Go to dashboard
            page.goto("https://app.constructconnect.com/dashboard", timeout=60000)
            page.wait_for_load_state("domcontentloaded", timeout=60000)
            time.sleep(10)
            
            # Find and use search bar
            search_input = page.locator("input[placeholder*='Search'], input[type='search'], [aria-label='Search']").first
            if search_input.is_visible():
                print(f"Searching for project {project_id}...")
                search_input.fill(str(project_id))
                time.sleep(2)
                search_input.press("Enter")
                time.sleep(15)
                
                # Click first result
                print("Clicking first result...")
                # Try generic result row or link containing ID
                result_link = page.locator(f"a[href*='{project_id}'], div[role='row']").first
                if result_link.is_visible():
                    print("Found a result row/link, clicking...")
                    result_link.click()
                    time.sleep(15)
                    
                    # Re-check for documents button
                    for selector in doc_tab_selectors:
                        try:
                            print(f"Re-checking for documents tab: {selector}")
                            btn = page.locator(selector).first
                            if btn.is_visible(timeout=2000):
                                docs_btn = btn
                                print(f"Found documents button after search: {selector}")
                                break
                        except:
                            continue
                else:
                    print("No search results found")
            else:
                print("Could not find global search bar")
                
        except Exception as e:
            print(f"Global search fallback failed: {e}")
            page.screenshot(path="debug_search_fallback_error.png")

    if docs_btn:
        print("Opening documents tab...")
        
        # This opens a new tab
        try:
            with context.expect_page() as new_page_info:
                docs_btn.click()
            
            docs_page = new_page_info.value
            docs_page.wait_for_load_state("domcontentloaded", timeout=60000)
            print("Documents tab opened")
            time.sleep(10)
            
            # Click Select All
            select_all = docs_page.locator("button:has-text('Select All')")
            if select_all.is_visible(timeout=5000):
                select_all.click()
                print("Clicked Select All")
                time.sleep(2)
            
            # Look for download button - prioritize "Download All"
            download_selectors = [
                "button:has-text('Download All')",
                "a:has-text('Download All')",
                "button:has-text('Download')",
                "a:has-text('Download')",
                "button:has-text('download')",
                "[data-action='download']",
                "button[title*='Download']"
            ]
            
            download_btn = None
            for selector in download_selectors:
                try:
                    btn = docs_page.locator(selector).first
                    if btn.is_visible(timeout=2000):
                        download_btn = btn
                        print(f"Found Download button: {selector}")
                        break
                except:
                    continue
            
            if download_btn:
                print("Downloading all documents...")
                with docs_page.expect_download(timeout=300000) as download_info:
                    download_btn.click()
                
                download = download_info.value
                download_path = os.path.join(download_dir, "documents.zip")
                download.save_as(download_path)
                print(f"Downloaded to {download_path}")
                return download_path
            else:
                print("No download button found on documents page")
                docs_page.screenshot(path="debug_docs_page_no_dl.png")
                
        except Exception as e:
            print(f"Error handling documents tab: {e}")
            page.screenshot(path="debug_docs_error.png")
            
    else:
        print("No documents button found on project page")
        page.screenshot(path="debug_project_page.png")
        print("Saved debug screenshot: debug_project_page.png")
        # Log body text to see what's on page
        try:
            text = page.locator("body").inner_text()
            print(f"Page text (first 500 chars): {text[:500]}")
        except:
            pass
            
    return None


def upload_to_odoo(opportunity_id, zip_path):
    """Upload documents to Odoo"""
    print(f"Uploading documents to Odoo opportunity {opportunity_id}...")
    
    # Debug: print connection info
    print(f"ODOO_URL: {ODOO_URL}")
    print(f"ODOO_DB: {ODOO_DB}")
    print(f"ODOO_USER: {ODOO_USER}")
    print(f"ODOO_PASSWORD set: {bool(ODOO_PASSWORD)}")
    
    if not all([ODOO_URL, ODOO_DB, ODOO_USER, ODOO_PASSWORD]):
        print("ERROR: Missing Odoo connection settings")
        return False
    
    # Connect to Odoo
    try:
        url = f"{ODOO_URL}/xmlrpc/2/common"
        print(f"Connecting to {url} ...")
        common = xmlrpc.client.ServerProxy(url)
        uid = common.authenticate(ODOO_DB, ODOO_USER, ODOO_PASSWORD, {})
        print(f"Authenticated successfully, uid={uid}")
    except Exception as e:
        print(f"Odoo connection error: {e}")
        return False
    
    if not uid:
        print("Failed to authenticate with Odoo - check username/password")
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
        print("Usage: python cc_fetch_worker.py <project_id> <opportunity_id> [source_url]")
        sys.exit(1)
    
    project_id = sys.argv[1]
    opportunity_id = sys.argv[2]
    source_url = sys.argv[3] if len(sys.argv) > 3 else None
    
    print(f"Starting fetch for CC Project {project_id}, Odoo Opportunity {opportunity_id}")
    if source_url:
        print(f"Using source URL: {source_url}")
    
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
            zip_path = fetch_documents(page, context, project_id, download_dir, source_url)
            
            browser.close()
        
        if zip_path and os.path.exists(zip_path):
            # Upload to Odoo
            upload_to_odoo(opportunity_id, zip_path)
            print("Done!")
        else:
            print("No documents downloaded")


if __name__ == "__main__":
    main()
