import boto3
from moto import mock_aws
import json

# --- THE MOCK LIMS DATABASE ---
lims_db = {"EXP-402": {"status": "IDLE", "version": 1}}


@mock_aws
def run_biotech_simulation():
    # 1. SETUP S3 (Scenario 26: The Ghost Bucket)
    s3 = boto3.client("s3", region_name="us-east-1")
    s3.create_bucket(Bucket="pm-analysis-results-2026")

    # 2. THE WEBHOOK DATA (This is what Benchling would send)
    benchling_payload = {
        "entity": {
            "id": "EXP-402",
            "fields": {"Mass Spec Data": {"value": "m/z: 450, intensity: 1200"}},
        }
    }

    # 3. THE PROCESSING LOGIC (The "Chinese" instructions translated)
    print("--- STARTING SIMULATION ---")

    # Extracting data
    sample_id = benchling_payload["entity"]["id"]
    raw_data = benchling_payload["entity"]["fields"]["Mass Spec Data"]["value"]
    print(f"Step 1: Extracted {sample_id}")

    # Uploading to S3
    s3_key = f"raw_data/{sample_id}.dat"
    s3.put_object(Bucket="pm-analysis-results-2026", Key=s3_key, Body=raw_data)
    s3_uri = f"s3://pm-analysis-results-2026/{s3_key}"
    print(f"Step 2: Saved raw data to {s3_uri}")

    # Updating LIMS (Scenario 30: Optimistic Locking)
    # We find the record and bump the version
    lims_db[sample_id]["status"] = "COMPLETED"
    lims_db[sample_id]["s3_path"] = s3_uri
    lims_db[sample_id]["version"] += 1
    print(f"Step 3: Updated LIMS Ledger to Version {lims_db[sample_id]['version']}")

    # 4. THE FINAL RESULT
    print("\n--- FINAL STATE OF LIMS DATABASE ---")
    print(json.dumps(lims_db, indent=2))


if __name__ == "__main__":
    run_biotech_simulation()
