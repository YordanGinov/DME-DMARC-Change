import hashlib
import hmac
import json
import os
import time
from email.utils import formatdate

import requests

# =====================
# CONFIGURATION
# =====================

BASE_URL = "https://api.dnsmadeeasy.com/V2.0"
REQUEST_SLEEP = 2

# Known DMARC policies that need updating
KNOWN_DMARC_POLICIES = {
    # add any known DMARC records here
}

# Domains to ignore (business critical domains)
DOMAINS_TO_IGNORE = {
    # Add domains here as needed
}

# =====================
# DMARC NORMALIZATION
# =====================

def normalize_dmarc(record: str) -> str:
    """
    Normalize DMARC record for comparison:
    - strips quotes
    - splits on semicolons
    - lowercases tag names
    - sorts tags alphabetically
    """
    record = record.strip().strip('"')
    parts = [
        p.strip()
        for p in record.split(";")
        if p.strip() and "=" in p
    ]
    
    parsed = []
    for part in parts:
        tag, value = part.split("=", 1)
        parsed.append((tag.lower().strip(), value.strip()))
    
    parsed.sort(key=lambda x: x[0])
    return "; ".join(f"{tag}={value}" for tag, value in parsed)

NORMALIZED_KNOWN_DMARC_RECORDS = {
    normalize_dmarc(p) for p in KNOWN_DMARC_POLICIES
}

# =====================
# AUTH HEADERS
# =====================

def generate_headers(api_key, secret_key):
    """Generate DME API authentication headers"""
    date_string = formatdate(usegmt=True)
    signature = hmac.new(
        secret_key.encode("utf-8"),
        date_string.encode("ascii"),
        hashlib.sha1
    ).hexdigest()
    
    return {
        "x-dnsme-apiKey": api_key,
        "x-dnsme-requestDate": date_string,
        "x-dnsme-hmac": signature,
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Connection": "close",
    }

# =====================
# API CALLS
# =====================

def get_domains(api_key, secret_key):
    """Retrieve all managed domains from DNSMadeEasy"""
    url = f"{BASE_URL}/dns/managed"
    resp = requests.get(url, headers=generate_headers(api_key, secret_key))
    resp.raise_for_status()
    return resp.json()["data"]

def get_domain_records(api_key, secret_key, domain_id):
    """Retrieve all records for a specific domain"""
    url = f"{BASE_URL}/dns/managed/{domain_id}/records"
    resp = requests.get(url, headers=generate_headers(api_key, secret_key))
    resp.raise_for_status()
    return resp.json().get("data", [])

# =====================
# DMARC PROCESSING
# =====================

def extract_dmarc_records(api_key, secret_key, domains):
    """
    Extract domains with DMARC records that need updating.
    Writes results immediately to file for data persistence.
    """
    count = 1
    domains_without_dmarc = 0
    domains_with_dmarc = 0
    
    # Clear output files
    open("domains_without_dmarc.txt", "w").close()
    open("domains_with_dmarc.txt", "w").close()
    
    for domain in domains:
        time.sleep(REQUEST_SLEEP)
        
        print(f"Processing domain {count}: {domain['name']}")
        count += 1
        
        domain_name = domain["name"]
        domain_id = domain["id"]
        
        try:
            records = get_domain_records(api_key, secret_key, domain_id)
            has_dmarc = False
            
            for record in records:
                if record["type"] == "TXT" and record.get("name", "").lower() == "_dmarc":
                    has_dmarc = True
                    value = record.get("value", "")
                    normalized_value = normalize_dmarc(value)
                    record_id = record["id"]
                    
                    # Check if it's a known policy that needs updating
                    if (normalized_value in NORMALIZED_KNOWN_DMARC_RECORDS 
                        and domain_name not in DOMAINS_TO_IGNORE):
                        # Write immediately to preserve data on failure
                        with open("domains_with_dmarc.txt", "a") as f:
                            f.write(f"{domain_name}:{domain_id}:{record_id}:{normalized_value}\n")
                        domains_with_dmarc += 1
                    break
            
            # If no DMARC record found, add to list
            if not has_dmarc and domain_name not in DOMAINS_TO_IGNORE:
                with open("domains_without_dmarc.txt", "a") as f:
                    f.write(f"{domain_name}:{domain_id}\n")
                domains_without_dmarc += 1
                    
        except Exception as e:
            print(f"Warning: Error processing domain {domain_name}: {str(e)}")
            continue
    
    print("-" * 50)
    print(f"DMARC extraction complete")
    print(f"   Domains without DMARC records: {domains_without_dmarc}")
    print(f"   Domains with non-compliant DMARC: {domains_with_dmarc}")
    print("-" * 50)

def update_dmarc_records(api_key, secret_key):
    """
    Update DMARC records (add new or update existing).
    Processes both domains_with_dmarc.txt and domains_without_dmarc.txt
    in a single unified operation.
    """
    # New DMARC record to apply
    new_dmarc_value = "v=DMARC1; p=reject; sp=reject; fo=1"
    
    dmarc_record = {
        "type": "TXT",
        "name": "_dmarc",
        "value": new_dmarc_value,
        "gtdLocation": "DEFAULT",
        "ttl": 3600
    }
    
    count = 0
    success_count = 0
    failed_count = 0
    
    # Update existing DMARC records
    if os.path.exists("domains_with_dmarc.txt"):
        print("\nUpdating existing DMARC records...")
        with open("domains_with_dmarc.txt", "r") as f:
            for line in f:
                time.sleep(REQUEST_SLEEP)
                
                # Extract domain first so it's always available for error reporting
                domain = line.split(":")[0].strip()
                
                try:
                    parts = line.strip().split(":", 3)
                    if len(parts) < 4:
                        continue
                    
                    domain, domain_id, record_id, _ = parts
                    count += 1
                    
                    print(f"({count}) Updating: {domain}")
                    
                    url = f"{BASE_URL}/dns/managed/{domain_id}/records/{record_id}"
                    response = requests.put(
                        url, 
                        headers=generate_headers(api_key, secret_key), 
                        data=json.dumps(dmarc_record)
                    )
                    
                    if response.status_code == 200:
                        print(f"    Success: Updated DMARC record for {domain}")
                        success_count += 1
                    else:
                        print(f"    Failed to update {domain}. Status: {response.status_code}")
                        failed_count += 1
                        
                except Exception as e:
                    print(f"    Error updating {domain}: {str(e)}")
                    failed_count += 1
                    continue
    
    # Add new DMARC records
    if os.path.exists("domains_without_dmarc.txt"):
        print("\nAdding new DMARC records...")
        with open("domains_without_dmarc.txt", "r") as f:
            for line in f:
                time.sleep(REQUEST_SLEEP)
                
                # Extract domain first so it's always available for error reporting
                domain = line.split(":")[0].strip()
                
                try:
                    parts = line.strip().split(":")
                    if len(parts) < 2:
                        continue
                    
                    domain, domain_id = parts[0], parts[1]
                    count += 1
                    
                    print(f"({count}) Adding: {domain}")
                    
                    url = f"{BASE_URL}/dns/managed/{domain_id}/records"
                    response = requests.post(
                        url, 
                        headers=generate_headers(api_key, secret_key), 
                        data=json.dumps(dmarc_record)
                    )
                    
                    if response.status_code == 201:
                        print(f"    Success: Added DMARC record for {domain}")
                        success_count += 1
                    else:
                        print(f"    Failed to add for {domain}. Status: {response.status_code}")
                        failed_count += 1
                        
                except Exception as e:
                    print(f"    Error adding for {domain}: {str(e)}")
                    failed_count += 1
                    continue
    
    print("-" * 50)
    print(f"DMARC update complete")
    print(f"   Successful updates: {success_count}")
    print(f"   Failed updates: {failed_count}")
    print("-" * 50)

# =====================
# MAIN MENU
# =====================

def main():
    """Main menu loop"""
    print("\n" + "=" * 60)
    print("DNSMadeEasy DMARC Record Manager")
    print("=" * 60)
    
    # Get credentials from user
    api_key = input("\nEnter your API Key: ").strip()
    secret_key = input("Enter your API Secret: ").strip()
    
    if not api_key or not secret_key:
        print("Error: API Key and Secret are required")
        return
    
    while True:
        print("\nSelect an option:")
        print("1. Extract domains with invalid DMARC records")
        print("2. Update DMARC records (add new or update existing)")
        print("3. Exit")
        
        choice = input("\nEnter your choice (1-3): ").strip()
        
        if choice == "1":
            try:
                print("\nRetrieving all domains...")
                domains = get_domains(api_key, secret_key)
                print(f"Found {len(domains)} domains")
                extract_dmarc_records(api_key, secret_key, domains)
            except Exception as e:
                print(f"Error: {str(e)}")
                
        elif choice == "2":
            try:
                update_dmarc_records(api_key, secret_key)
            except Exception as e:
                print(f"Error: {str(e)}")
                
        elif choice == "3":
            print("Exiting...")
            break
        else:
            print("Invalid choice. Please enter 1, 2, or 3.")

if __name__ == "__main__":
    main()