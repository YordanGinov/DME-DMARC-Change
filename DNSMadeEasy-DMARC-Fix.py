import hmac
import hashlib
from email.utils import formatdate
import requests
import json
import time

#Generates headers based on current location time and date as per DME documentation
def generate_dnsme_headers(api_key, secret_key):
    #print("Generating DNSMadeEasy headers...")
    # Generate current UTC date in HTTP format
    date_string = formatdate(timeval=None, localtime=False, usegmt=True)
    
    # Create HMAC SHA1 hash
    key_bytes = secret_key.encode('utf-8')
    message_bytes = date_string.encode('utf-8')
    hmac_hash = hmac.new(key_bytes, message_bytes, hashlib.sha1).hexdigest()
    
    # Build headers
    headers = {
        "x-dnsme-apiKey": api_key,
        "x-dnsme-requestDate": date_string,
        "x-dnsme-hmac": hmac_hash,
        "Content-Type": "application/json",
        "Connection": "close",
    }
    return headers

#Retrieve all domains
def get_domains(api_key, secret_key, url):
    print("Retrieving domains...")
    url = f"{base_url}dns/managed/"
    generated_headers=generate_dnsme_headers(api_key, secret_key)
    domains_json = requests.get(url, headers=generated_headers)
    
    if domains_json.status_code == 200:
        domains_json = domains_json.json()
        return domains_json.get("data", [])
    else:
        domains_json.raise_for_status()
        return domains_json.get("data", [])

#Retrieve domain records for each domain
def get_specific_domain_records(domains):
    print("Retrieving domain records...")
    count = 1
    domain_with_records = {}
    domain_ids = [domain['id'] for domain in domains]
    for id in domain_ids:
        time.sleep(2)
        print(f"Domain number: {count}")
        count += 1
        generated_headers=generate_dnsme_headers(api_key, secret_key)
        url = f"{base_url}dns/managed/{id}/records/"
        records_json = requests.get(url, headers=generated_headers)
        if records_json.status_code == 200:
            records_json = records_json.json()
            domain_name = next((d['name'] for d in domains if d['id'] == id))
            domain_with_records[domain_name] = {
                "domain_id": id,
                "records": records_json.get("data", [])
            }
        else:
            records_json.raise_for_status()
    return domain_with_records


# Check for domains without DMARC records
def get_domain_without_dmarc_record(dns_records):
    print("Checking for domains without DMARC records...")
    for domains, payload in dns_records.items():
            domain_id = payload["domain_id"]
            records = payload["records"]
            has_dmarc = any(record['type'] == 'TXT' and "v=DMARC" in record['value'] for record in records)
            if not has_dmarc:
                with open("domains_without_dmarc.txt", "a") as f:
                    f.write(f"{domains}:{domain_id}\n")
            else:
                for record in records:
                    if (record["type"] == "TXT"
                    and record.get("name", "").lower() == "_dmarc") : 
                        record_id = record["id"]
                        record_value = record["value"]
                        with open("domains_with_dmarc.txt", "a") as f:
                            f.write(f"{domains}:{domain_id}:{record_id}:{record_value}\n")
    return None

#Add DMARC record
def add_dmarc_record(line):
        #Parse domain name and id
        time.sleep(2)
        domain, domain_id = ln.strip().split(":")

        dmarc_record = {
                "type": "TXT",
                "name": "_dmarc",
                "value": "v=DMARC1; p=reject; sp=reject; fo=1",
                "gtdLocation": "DEFAULT",
                "ttl": 3600
            }
        generated_headers=generate_dnsme_headers(api_key, secret_key)
        request_url = f"{base_url}dns/managed/{domain_id}/records"
        #print(f"Domain: {domain},Domain ID: {domain_id}\n Record details:\n{dmarc_record}\n URL: {request_url} \n\n")
        response = requests.post(request_url, headers = generated_headers, data=json.dumps(dmarc_record))
        if response.status_code == 201:
            print(f"DMARC record added for domain: {domain}")
        else:
            print(f"Failed to add DMARC record for domain: {domain}. Status code: {response.status_code} {response.text}")

# Production Details
api_key = "de4beed6-e415-44b2-b30c-b0e86c942e9b"
secret_key = "b9ce5f47-f1c4-4e47-b417-f29e8471e49d"
base_url="https://api.dnsmadeeasy.com/V2.0/"

# Sandbox Environment
"""api_key = "e03666d0-19f4-46bb-ad47-d3d9659f9093"
secret_key = "d86a71e3-aa6e-4015-a348-5639aec87593"
base_url = "https://api.sandbox.dnsmadeeasy.com/V2.0/" """

print(f"This script is developed to perform multiple tasks. Please select the task you want to be completed:")
print(f"1. Create report with domains without DNS records")
print("2. Update DNS records based on created report")
print("3. Exit script execution")
user_choice = input("Please choose an option: ")

#Setting function results to variables in order to not repeat API calls
while user_choice != "3":
    if user_choice == "1":
        open("domains_with_dmarc.txt", "w").close()
        open("domains_without_dmarc.txt" , "w").close()
        retrieved_domains = get_domains(api_key, secret_key, base_url)
        domain_records = get_specific_domain_records(retrieved_domains)
        domains_without_dmarc = get_domain_without_dmarc_record(domain_records)
        print("-----------------")
        print(f"All domains are retrieved and checked for DMARC records. Please check the report file: domains_without_dmarc.txt")
        print("-----------------")
    elif user_choice == "2":
        with open ("domains_without_dmarc.txt") as f:
            for ln in f:
                print(ln)
                add_dmarc_record(ln)
    else:
        print("Invalid Input. Please select between 1, 2, 3.")
    print("Make your selection: ")
    user_choice = input()