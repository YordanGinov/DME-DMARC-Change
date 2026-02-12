import time
import json
import requests
import hmac
import hashlib
from email.utils import formatdate
from datetime import datetime

# =====================
# CONFIGURATION
# =====================

#Test Account - Remove the tripple quotation mark to activate this.
"""API_KEY = "e03666d0-19f4-46bb-ad47-d3d9659f9093"
API_SECRET = "d86a71e3-aa6e-4015-a348-5639aec87593"
BASE_URL = "https://api.sandbox.dnsmadeeasy.com/V2.0" """

#Live Domains! DO NOT TOUCH! - add tripple quotation marks to deactivate these credentials
API_KEY = "de4beed6-e415-44b2-b30c-b0e86c942e9b"
API_SECRET = "b9ce5f47-f1c4-4e47-b417-f29e8471e49d"
BASE_URL = "https://api.dnsmadeeasy.com/V2.0"

# basic rate limiting
REQUEST_SLEEP = 2  

# KNOWN DMARC POLICIES
KNOWN_DMARC_POLICIES = {
    "v=DMARC1; p=none",
    "v=DMARC1; p=none; rua=mailto:wo1jenvz@ag.dmarcian-eu.com; ruf=mailto:wo1jenvz@fr.dmarcian-eu.com",
    "v=DMARC1; p=none; fo=1; rua=mailto:dmarc_rua@emaildefense.proofpoint.com; ruf=mailto:dmarc_ruf@emaildefense.proofpoint.com",
    "v=DMARC1; p=none; rua=mailto:d16f414973433f6dfc99afb4173347fd-t@dmarc.report-uri.com",
    "v=DMARC1; p=reject; sp=none; pct=40; aspf=r; fo=1; rua=mailto:postmaster@ubrewards.com; ruf=mailto:postmaster@ubrewards.com",
}

#List of domains that must not go through the script
DOMAINS_TO_IGNORE = {
    "perkz.com",
    "perkz.net",
    "rewardgateway4.co.uk",
    "rewardgateway.com",
    "rewardgateway.com.au",
    "reward-gateway.co.uk",
    "rewardgateway.co.uk",
    "rewardgateway.ie",
    "rewardgateway.net",
    "rewardgatewayuat.com",
    "rgcycletowork.co.uk",
    "appreciation-awards.com",
    "asperity360.com",
    "asperity360.co.uk",
    "asperity.com",
    "asperity.com.au",
    "asperity.co.nz",
    "asperity.co.uk",
    "asperity.dk",
    "asperityemployeebenefits.com",
    "asperityemployeebenefits.co.uk",
    "asperityfreetrial.co.uk",
    "asperity.ie",
    "aspirerewards.co.uk",
    "boomforrgpeople.com",
    "brandintegrity.com",
    "clarkwoodenterprise.com",
    "clarkwoodenterprise.co.uk",
    "clarkwoodenterprise.uk",
    "engagementexcellence.com",
    "stafftreats.com",
    "xexec.com"
}


def normalize_dmarc(record: str) -> str:
    """
    Minimal DMARC normalizer:
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

# AUTH HEADERS
def generate_headers():
    date_string = formatdate(usegmt=True)
    signature = hmac.new(
        API_SECRET.encode("utf-8"),
        date_string.encode("ascii"),
        hashlib.sha1
    ).hexdigest()

    return {
        "x-dnsme-apiKey": API_KEY,
        "x-dnsme-requestDate": date_string,
        "x-dnsme-hmac": signature,
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Connection": "close",
    }


# API CALLS
def get_domains():
    url = f"{BASE_URL}/dns/managed"
    resp = requests.get(url, headers=generate_headers())
    resp.raise_for_status()
    return resp.json()["data"]

def get_domain_records(domain_id):
    url = f"{BASE_URL}/dns/managed/{domain_id}/records"
    resp = requests.get(url, headers=generate_headers())
    resp.raise_for_status()
    return resp.json().get("data", [])

# DMARC EXTRACTION
def extract_matching_dmarc(domains):
    count = 1
    with open("domains_with_dmarc.txt", "w") as f:
        for domain in domains:
            time.sleep(REQUEST_SLEEP)

            #Logging to know the progress of the script
            print(count)
            count += 1

            #Extracting domain details
            domain_name = domain["name"]
            domain_id = domain["id"]
            records = get_domain_records(domain_id)

            
            for record in records:
                if (
                    record["type"] == "TXT"
                    and record.get("name", "").lower() == "_dmarc"
                ):
                    value = record.get("value", "")
                    normalized_value = normalize_dmarc(value)
                    if (
                        normalized_value in NORMALIZED_KNOWN_DMARC_RECORDS
                        and domain_name not in DOMAINS_TO_IGNORE
                    ):
                        
                        record_id = record["id"]
                        f.write(
                            f"{domain_name}:{domain_id}:{record_id}:{normalized_value}\n"
                        )
        print(f"✅ DMARC extraction complete")

def update_dmarc_record(line):
        #Parse domain name and id
        time.sleep(REQUEST_SLEEP)
        domain, domain_id, record_id, _ = ln.strip().split(":", 3)

        dmarc_record = {
                "type": "TXT",
                "name": "_dmarc",
                "value": "v=DMARC1; p=reject; sp=reject; fo=1",
                "gtdLocation": "DEFAULT",
                "ttl": 3600,
                "id": f"{record_id}"
            }
        request_url = f"{BASE_URL}/dns/managed/{domain_id}/records/{record_id}"
        response = requests.put(request_url, headers = generate_headers(), data=json.dumps(dmarc_record))
        if response.status_code == 200:
            print(f"DMARC record updated for domain: {domain}")
        else:
            print(f"Failed to add DMARC record for domain: {domain}. Status code: {response.status_code} {response.text}")

print(f"This script is developed to perform multiple tasks. Please select the task you want to be completed:")
print(f"1. Create report with domains with invalid DMARC DNS records")
print("2. Update DNS records based on created report")
print("3. Exit script execution")
user_choice = input("Please choose an option: ")

#Setting function results to variables in order to not repeat API calls
while user_choice != "3":
    if user_choice == "1":
        open("domains_with_dmarc.txt", "w").close()
        domains = get_domains()
        extract_matching_dmarc(domains)
        print("-----------------")
        print(f"All domains are retrieved and checked for DMARC records. Please check the report file: domains_with_dmarc.txt")
        print("-----------------")
    elif user_choice == "2":
        count = 0
        with open ("domains_with_dmarc.txt") as f:
            for ln in f:
                count +=1
                print(count)
                update_dmarc_record(ln)
    else:
        print("Invalid Input. Please select between 1, 2, 3.")
    print("Make your selection: ")
    user_choice = input()
