#!/usr/bin/env python3
"""
Real-time dashboard for monitoring the bot swarm.
This script reads statistics from individual bot files and aggregates them.
"""
import os
import time
import json
from collections import defaultdict

STATS_DIR = "/tmp/bot_stats"

def clear_screen():
    """Clears the terminal screen."""
    os.system('cls' if os.name == 'nt' else 'clear')

def main():
    """Main loop to read stats and display the dashboard."""
    print("🚀 Starting Swarm Dashboard...")
    print(f"👀 Watching for stats in: {STATS_DIR}")
    time.sleep(2)

    if not os.path.exists(STATS_DIR):
        print(f"❌ Error: Statistics directory not found at {STATS_DIR}.")
        print("   Is the swarm running?")
        return

    start_time = time.time()
    try:
        while True:
            bot_files = [f for f in os.listdir(STATS_DIR) if f.endswith('.json')]
            
            if not bot_files:
                print("\r⏳ Waiting for bots to report stats...", end="", flush=True)
                time.sleep(1)
                continue

            # --- Data Aggregation ---
            total_completed = 0
            total_success = 0
            total_failed = 0
            total_rate = 0.0
            aggregated_status_codes = defaultdict(int)
            aggregated_error_types = defaultdict(int)
            active_bots = 0
            
            for filename in bot_files:
                try:
                    with open(os.path.join(STATS_DIR, filename), 'r') as f:
                        data = json.load(f)
                    
                    # Consider a bot stale if it hasn't reported in 15 seconds
                    if time.time() - data.get('timestamp', 0) > 15:
                        continue
                    
                    active_bots += 1
                    total_completed += data.get('completed', 0)
                    total_success += data.get('success', 0)
                    total_failed += data.get('failed', 0)
                    total_rate += data.get('rate', 0)
                    
                    for code, count in data.get('status_codes', {}).items():
                        aggregated_status_codes[code] += count
                    for error, count in data.get('error_types', {}).items():
                        aggregated_error_types[error] += count

                except (json.JSONDecodeError, FileNotFoundError):
                    # Ignore errors from partially written or deleted files
                    continue

            # --- Display ---
            clear_screen()
            elapsed_time = time.time() - start_time
            
            print("="*80)
            print("📊 SWARM DASHBOARD - REAL-TIME STATISTICS")
            print("="*80)
            
            print(f"  🕒 Running for: {time.strftime('%H:%M:%S', time.gmtime(elapsed_time))}   |   🤖 Active Bots: {active_bots}/{len(bot_files)}")
            
            print("\n--- AGGREGATE PERFORMANCE ---")
            success_rate_percent = (total_success / total_completed * 100) if total_completed > 0 else 0
            print(f"  ⚡ Total Requests/Sec: {total_rate:,.1f}")
            print(f"  ✅ Total Success:      {total_success:,.0f} ({success_rate_percent:.1f}%)")
            print(f"  ❌ Total Failed:       {total_failed:,.0f}")

            if aggregated_status_codes:
                print("\n--- HTTP STATUS CODES (Top 5) ---")
                sorted_codes = sorted(aggregated_status_codes.items(), key=lambda item: item[1], reverse=True)
                for code, count in sorted_codes[:5]:
                    print(f"  - {code}: {count:,.0f}")

            if aggregated_error_types:
                print("\n--- ERROR TYPES (Top 5) ---")
                sorted_errors = sorted(aggregated_error_types.items(), key=lambda item: item[1], reverse=True)
                for error, count in sorted_errors[:5]:
                    print(f"  - {error}: {count:,.0f}")
            
            print("\n" + "="*80)
            print("Press Ctrl+C to exit the dashboard (the swarm will keep running).")

            time.sleep(1)

    except KeyboardInterrupt:
        print("\n\n🛑 Dashboard stopped. The swarm continues to run in the background.")
        print(f"   To stop the entire swarm, run: tmux kill-session -t bot_swarm")
    except Exception as e:
        print(f"\nAn error occurred: {e}")

if __name__ == "__main__":
    main()
