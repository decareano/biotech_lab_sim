import time
import random
import sys

# Set random seed for predictability during testing
# random.seed(42)


def validate_api_access(token):
    valid_key = {"dev1234": "active", "prod4321": "active"}

    if token not in valid_key:
        raise PermissionError(f"not in keys")
    print(f"correct API called")


def validate_protein_metrics(value_string):
    """Scenario 40: Data Quality Gatekeeper."""
    # Defensive programming: check if label exists
    parts = value_string.split("intensity: ")
    if len(parts) < 2:
        raise ValueError("Data Format Error: 'intensity: ' not found in payload.")

    # Defensive programming: check if valid number
    intensity = float(parts[1])
    if intensity < 0:
        raise ValueError(f"SCIENTIFIC IMPOSSIBILITY: Value {intensity} is negative.")

    print(f"✅ Data Sanity Check Passed: {intensity} is valid.")


def upload_to_lims(data, max_retries=3):
    """Scenario 41: Network Resilience Gatekeeper."""
    for attempt in range(1, max_retries + 1):
        try:
            print(f"Attempt {attempt}: Connecting to AWS / Benchling...")

            # Simulate a flaky network: Capture and display the dice roll
            roll = random.random()
            print(f"🎲 Dice Roll: {roll:.2f}")

            if roll < 0.66:
                raise ConnectionError(f"Network timeout (Roll was {roll:.2f}).")

            print("✅ Upload Successful to LIMS.")
            return True  # Success, exit the function

        except ConnectionError as e:
            print(f"⚠️ Attempt {attempt} failed: {e}")

            if attempt < max_retries:
                # Exponential backoff
                wait_time = 1 * attempt
                print(f"Retrying in {wait_time}s...")
                time.sleep(wait_time)
            else:
                # Max retries reached
                print("🚨 Max retries reached. Upload Failed.")
                raise  # The naked raise: passes the original error up


def run_biotech_pipeline(payload, api_key):
    """The Orchestrator Function: Manages Security, QC, and Transmission."""
    try:
        # Step 1: Secure the connection (Scenario 42)
        validate_api_access(api_key)

        # Step 2: Extraction
        raw_val = payload["entity"]["fields"]["Mass Spec Data"]["value"]

        # Step 3: Validate (Scenario 40)
        validate_protein_metrics(raw_val)

        # Step 4: Transmit (Scenario 41)
        upload_to_lims(raw_val)

        print("Pipeline Execution: COMPLETED SUCCESSFULLY.")

    except (PermissionError, ValueError, ConnectionError):
        # The Manager handles the final crash report
        print("❌ PIPELINE EXECUTION: FAILED.")
        # Exit with 1 tells GitHub Actions that the job failed
        sys.exit(1)


if __name__ == "__main__":
    # Test Payload with good data
    test_payload = {
        "entity": {"fields": {"Mass Spec Data": {"value": "intensity: 500"}}}
    }

    # Use a valid key to run
    valid_key = "DEV_API_KEY_99X"
    run_biotech_pipeline(test_payload, valid_key)
