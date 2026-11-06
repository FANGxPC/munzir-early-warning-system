#!/usr/bin/env python3
"""
Munzir Sentinel Trace Replay Tool (Backup Demo Simulator).
Streams a pre-recorded node trace file to the Munzir REST API
with a clear [REPLAY] banner for live pitch resilience when
physical Wi-Fi or hardware is unavailable.
"""

import argparse
import json
import time
from pathlib import Path
import requests

DEFAULT_TRACE = Path(__file__).parent / "sample_trace.json"


def main():
    parser = argparse.ArgumentParser(description="Replay Sentinel node telemetry to Munzir API")
    parser.add_argument("--api-url", default="http://localhost:8000", help="Base URL of Munzir platform")
    parser.add_argument("--trace", default=str(DEFAULT_TRACE), help="Path to JSON trace file")
    parser.add_argument("--interval", type=float, default=2.0, help="Delay between replayed readings (seconds)")
    parser.add_argument("--commission-first", action="store_true", default=True, help="Auto-commission node before streaming")
    args = parser.parse_args()

    trace_path = Path(args.trace)
    if not trace_path.exists():
        print(f"[REPLAY] Error: Trace file not found: {trace_path}")
        return

    with open(trace_path, "r", encoding="utf-8") as f:
        readings = json.load(f)

    print("=" * 76)
    print("  🚨 MUNZIR SENTINEL TELEMETRY REPLAY RUNNER [DEMO BACKUP MODE] 🚨  ")
    print(f"  Streaming {len(readings)} readings to: {args.api_url}")
    print("=" * 76)

    # 1. Commission node if requested
    if args.commission_first and readings:
        first_node = readings[0].get("node_id", "SENT-001")
        comm_payload = {
            "node_id": first_node,
            "site_id": "SITE-JA-01",
            "latitude": 24.9920,
            "longitude": 55.0410,
            "accuracy_m": 12.0,
            "method": "browser_geolocation",
            "indoor_mode": False
        }
        try:
            r = requests.post(
                f"{args.api_url}/api/v1/sentinel/commission",
                json=comm_payload,
                headers={"X-Role": "employer_safety"},
                timeout=5
            )
            if r.status_code == 200:
                print(f"[REPLAY] ✔ Commissioned {first_node} at SITE-JA-01 (H3: {r.json().get('h3_index')})")
            else:
                print(f"[REPLAY] Commission notice: {r.status_code} - {r.text}")
        except Exception as e:
            print(f"[REPLAY] Warning: Could not auto-commission ({e}). Continuing...")

    print("\n[REPLAY] Starting telemetry transmission stream:\n")

    for idx, reading in enumerate(readings, 1):
        try:
            url = f"{args.api_url}/api/v1/sentinel/upload"
            resp = requests.post(
                url,
                json=reading,
                headers={"X-Sentinel-Key": "munzir_sentinel_secret_2026"},
                timeout=5
            )

            if resp.status_code == 200:
                data = resp.json()
                level = data.get("level", "None")
                wbgt = data.get("rederived_wbgt", reading.get("wbgt_est_c"))
                print(f"[REPLAY] [{idx}/{len(readings)}] Node: {reading['node_id']} | "
                      f"Air: {reading['air_temp_c']}°C | RH: {reading['rh_pct']}% | "
                      f"Globe: {reading['globe_temp_c']}°C => "
                      f"WBGT: {wbgt}°C | Level: >> {level.upper()} <<")
            else:
                print(f"[REPLAY] [{idx}/{len(readings)}] HTTP {resp.status_code}: {resp.text}")

        except Exception as e:
            print(f"[REPLAY] Transmission error: {e}")

        if idx < len(readings):
            time.sleep(args.interval)

    print("\n" + "=" * 76)
    print("  ✔ REPLAY STREAM COMPLETED. Dashboard view is updated live.")
    print("=" * 76)


if __name__ == "__main__":
    main()
