# import boto3
# from moto import mock_aws
# import json

# # --- THE MOCK LIMS DATABASE ---
# lims_db = {"EXP-402": {"status": "IDLE", "version": 1}}

# def validate_protein_metrics(value_string):
#     """
#     Parses the string and validates the numeric intensity.
#     """
#     try:
#         parts = value_string.split("intensity: ")


# @mock_aws
# def run_biotech_simulation():
#     # 1. SETUP S3 (Scenario 26: The Ghost Bucket)
#     s3 = boto3.client("s3", region_name="us-east-1")
#     # s3.create_bucket(Bucket="pm-analysis-results-2026")

#     # 2. THE WEBHOOK DATA (This is what Benchling would send)
#     benchling_payload = {
#         "entity": {
#             "id": "EXP-402",
#             "fields": {"Mass Spec Data": {"value": "m/z: 450, intensity: 1200"}},
#         }
#     }

#     # 3. THE PROCESSING LOGIC (The "Chinese" instructions translated)
#     print("--- STARTING SIMULATION ---")

#     # Extracting data
#     sample_id = benchling_payload["entity"]["id"]
#     raw_data = benchling_payload["entity"]["fields"]["Mass Spec Data"]["value"]
#     print(f"Step 1: Extracted {sample_id}")

#     # Uploading to S3
#     s3_key = f"raw_data/{sample_id}.dat"
#     s3.put_object(Bucket="pm-analysis-results-2026", Key=s3_key, Body=raw_data)
#     s3_uri = f"s3://pm-analysis-results-2026/{s3_key}"
#     print(f"Step 2: Saved raw data to {s3_uri}")

#     # Updating LIMS (Scenario 30: Optimistic Locking)
#     # We find the record and bump the version
#     lims_db[sample_id]["status"] = "COMPLETED"
#     lims_db[sample_id]["s3_path"] = s3_uri
#     lims_db[sample_id]["version"] += 1
#     print(f"Step 3: Updated LIMS Ledger to Version {lims_db[sample_id]['version']}")

#     # 4. THE FINAL RESULT
#     print("\n--- FINAL STATE OF LIMS DATABASE ---")
#     print(json.dumps(lims_db, indent=2))


# if __name__ == "__main__":
#     run_biotech_simulation()


import time
import random
import sys

# random.seed(42)


# scenario 40 validation
def validate_protein_metrics(value_string):
    parts = value_string.split("intensity: ")
    # I have: value = "1200" so positions 0 and 1 in index. less than that is an error
    # and I only need the position 1 since I am splitting string

    if len(parts) < 2:
        raise ValueError("Data format error: not found")
    intensity = float(parts[1])
    # here I am testing if I can pick up the string ie: "1200" otherwise is useless
    if intensity < 0:
        raise ValueError(
            f"scientifically impossible: value {intensity} cannot be negative"
        )
    # if not then succeds
    print(f"Data sanity check: {intensity} is valid")


# scenario 41 - network resiliance


def upload_to_lims(data, max_retries=3):
    # here we are going to test the three times we are going to test the network before
    # we declare an SOS on the network
    # using a loop construct
    for attempt in range(1, max_retries + 1):
        try:
            print(f"we are sending data to LIMS. Attempt {attempt} ")
            roll = random.random()
            print(f"Dice Roll: {roll:2f}")
            if roll < 0.66:
                raise ConnectionError("network unavailable")
            print(f"connection sucess")
            return True
        except ConnectionError as myError:
            print(f"attempt failed: {attempt} {myError}")
            if attempt < max_retries:
                print(f"this is retry number: {attempt}")
                wait_time = 1 * attempt
                print(f"waiting on: {wait_time}")
                time.sleep(wait_time)
            else:
                print(f"max retries failure. Connectivity error")
                raise


def run_biotech_pipeline(payload):
    # this is the orchestrator to test:
    # sample payload
    # validates the number is correct ie: 500.0 not -500.0
    # makes sure the network is tested three times before reporting a failure
    """The master pipeline."""
    try:
        # 1. Extract
        # payload is the param of the function and it takes a list of items
        raw_val = payload["entity"]["fields"]["Mass Spec Data"]["value"]

        # 2. Validate (Scenario 40)
        validate_protein_metrics(raw_val)

        # 3. Transmit (Scenario 41)
        upload_to_lims(raw_val)

        print("Pipeline Execution: SUCCESS.")

    except (ValueError, ConnectionError) as e:
        print(f"❌ PIPELINE FAILURE: {e}")
        # Final escalation to GitHub Actions (Red X)
        sys.exit(1)


if __name__ == "__main__":
    # Test Payload

    test_payload = {
        "entity": {"fields": {"Mass Spec Data": {"value": "intensity: 500"}}}
    }
    run_biotech_pipeline(test_payload)
