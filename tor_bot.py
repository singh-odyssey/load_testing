#!/usr/bin/env python3
"""
Tor Network Bot - Educational Project
Visits websites through Tor network with IP rotation using web browser
Advanced fingerprint randomization and human behavior simulation
"""

import time
import sys
import random
import os
import subprocess
from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from stem import Signal
from stem.control import Controller
import requests

class TorBot:
    def __init__(self):
        self.tor_control_port = 9051
        self.tor_password = ""
        self.tor_proxy_host = "127.0.0.1"
        self.tor_proxy_port = 9050
        self.driver = None
        self.user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/115.0",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:110.0) Gecko/20100101 Firefox/110.0",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:109.0) Gecko/20100101 Firefox/115.0",
            "Mozilla/5.0 (X11; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/115.0",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        ]
        self.screen_resolutions = [
            (1920, 1080), (1366, 768), (1440, 900), (1536, 864), (1280, 720)
        ]
        self.languages = [
            "en-US,en;q=0.9",
            "en-GB,en;q=0.9",
            "en-US,en;q=0.8",
        ]
        
    def ensure_tor_running(self):
        """Ensure Tor service is running, start if not"""
        try:
            # Check if Tor is running by checking the process
            result = subprocess.run(['pgrep', '-x', 'tor'], capture_output=True)
            if result.returncode != 0:
                print("⚠️  Tor is not running. Starting Tor...")
                # Kill any stale processes
                subprocess.run(['sudo', 'pkill', '-9', 'tor'], stderr=subprocess.DEVNULL)
                time.sleep(1)
                # Start Tor in background
                subprocess.Popen(['sudo', 'tor'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                print("⏳ Waiting for Tor to start...")
                time.sleep(5)
                # Verify it started
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
            return True  # Continue anyway
        
    def get_current_ip(self):
        """Get current IP address through Tor"""
        max_retries = 3
        for attempt in range(max_retries):
            try:
                session = requests.session()
                session.proxies = {
                    'http': f'socks5h://{self.tor_proxy_host}:{self.tor_proxy_port}',
                    'https': f'socks5h://{self.tor_proxy_host}:{self.tor_proxy_port}'
                }
                response = session.get('https://api.ipify.org?format=json', timeout=10)
                return response.json()['ip']
            except Exception as e:
                if attempt < max_retries - 1:
                    print(f"⏳ Retry {attempt + 1}/{max_retries}... Waiting for Tor...")
                    time.sleep(3)
                else:
                    print(f"Error getting IP: {e}")
                    return None
        return None
    
    def renew_tor_ip(self):
        """Request new Tor circuit to change IP"""
        try:
            with Controller.from_port(port=self.tor_control_port) as controller:
                controller.authenticate(password=self.tor_password)
                controller.signal(Signal.NEWNYM)
                wait_time = random.uniform(6, 10)
                print(f"Waiting {wait_time:.1f}s for new circuit...")
                time.sleep(wait_time)
                print("✓ New Tor circuit established")
                return True
        except Exception as e:
            print(f"Error renewing IP: {e}")
            return False
    
    def setup_browser(self):
        """Configure Firefox browser to use Tor with randomized fingerprint"""
        firefox_options = Options()
        
        # Randomize fingerprint
        user_agent = random.choice(self.user_agents)
        screen_res = random.choice(self.screen_resolutions)
        language = random.choice(self.languages)
        
        print(f"🎭 Randomizing fingerprint...")
        print(f"   User Agent: {user_agent[:50]}...")
        print(f"   Screen: {screen_res[0]}x{screen_res[1]}")
        print(f"   Language: {language.split(',')[0]}")
        
        # Configure Firefox to use Tor SOCKS proxy
        firefox_options.set_preference("network.proxy.type", 1)
        firefox_options.set_preference("network.proxy.socks", self.tor_proxy_host)
        firefox_options.set_preference("network.proxy.socks_port", self.tor_proxy_port)
        firefox_options.set_preference("network.proxy.socks_remote_dns", True)
        
        # Hide automation/webdriver flags
        firefox_options.set_preference("dom.webdriver.enabled", False)
        firefox_options.set_preference("useAutomationExtension", False)
        
        # Enhanced privacy settings
        firefox_options.set_preference("privacy.trackingprotection.enabled", True)
        firefox_options.set_preference("privacy.firstparty.isolate", True)
        
        # Disable WebRTC (can leak real IP)
        firefox_options.set_preference("media.peerconnection.enabled", False)
        
        # Disable geolocation
        firefox_options.set_preference("geo.enabled", False)
        
        # Disable telemetry
        firefox_options.set_preference("toolkit.telemetry.enabled", False)
        
        # Don't save passwords, forms, history
        firefox_options.set_preference("signon.rememberSignons", False)
        firefox_options.set_preference("browser.formfill.enable", False)
        
        # Disable cache
        firefox_options.set_preference("browser.cache.disk.enable", False)
        firefox_options.set_preference("browser.cache.memory.enable", False)
        
        # Randomized user agent
        firefox_options.set_preference("general.useragent.override", user_agent)
        
        # Randomized language
        firefox_options.set_preference("intl.accept_languages", language)
        
        # Disable battery API
        firefox_options.set_preference("dom.battery.enabled", False)
        
        # Disable device sensors
        firefox_options.set_preference("device.sensors.enabled", False)
        
        try:
            # Use geckodriver
            os.environ['MOZ_HEADLESS'] = '0'  # Show browser
            service = Service(log_path='/tmp/geckodriver.log')
            
            self.driver = webdriver.Firefox(service=service, options=firefox_options)
            self.driver.set_page_load_timeout(30)
            
            # Set window size to randomized resolution
            self.driver.set_window_size(screen_res[0], screen_res[1])
            
            # Store screen_res for later use
            self.current_screen_res = screen_res
            
            print("✓ Browser configured with randomized fingerprint")
            return True
        except Exception as e:
            print(f"Error setting up browser: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def inject_fingerprint_spoofing(self, screen_res):
        """Inject JavaScript to spoof browser fingerprints"""
        cpu_cores = random.choice([2, 4, 6, 8, 12, 16])
        device_memory = random.choice([4, 8, 16, 32])
        tz_offset = random.randint(-12, 12) * 60
        
        script = """
        Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
        Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
        Object.defineProperty(navigator, 'languages', {get: () => ['en-US', 'en']});
        Object.defineProperty(navigator, 'hardwareConcurrency', {get: () => %d});
        Object.defineProperty(navigator, 'deviceMemory', {get: () => %d});
        Object.defineProperty(screen, 'width', {get: () => %d});
        Object.defineProperty(screen, 'height', {get: () => %d});
        Date.prototype.getTimezoneOffset = function() { return -%d; };
        console.log('Fingerprint spoofing active');
        """ % (cpu_cores, device_memory, screen_res[0], screen_res[1], tz_offset)
        
        self.driver.execute_script(script)
    
    def simulate_human_behavior(self):
        """Simulate realistic human browsing behavior"""
        try:
            print("👤 Simulating human behavior...")
            
            page_height = self.driver.execute_script("return document.body.scrollHeight")
            viewport_height = self.driver.execute_script("return window.innerHeight")
            
            time.sleep(random.uniform(1.5, 3.5))
            
            current_position = 0
            scroll_sessions = random.randint(3, 7)
            
            for i in range(scroll_sessions):
                scroll_distance = random.randint(150, 500)
                current_position += scroll_distance
                
                if current_position > page_height - viewport_height:
                    current_position = page_height - viewport_height
                
                self.driver.execute_script(f"window.scrollTo({{top: {current_position}, behavior: 'smooth'}});")
                time.sleep(random.uniform(0.8, 3.2))
                
                if random.random() < 0.3:
                    scroll_back = random.randint(50, 150)
                    current_position -= scroll_back
                    self.driver.execute_script(f"window.scrollTo({{top: {current_position}, behavior: 'smooth'}});")
                    time.sleep(random.uniform(0.5, 1.5))
            
            try:
                action = ActionChains(self.driver)
                for _ in range(random.randint(2, 5)):
                    x_offset = random.randint(-200, 200)
                    y_offset = random.randint(-200, 200)
                    action.move_by_offset(x_offset, y_offset)
                    action.perform()
                    time.sleep(random.uniform(0.3, 0.8))
                    action.reset_actions()
            except:
                pass
            
            if random.random() < 0.5:
                try:
                    elements = self.driver.find_elements(By.TAG_NAME, "a")
                    if elements:
                        random_element = random.choice(elements[:10])
                        action = ActionChains(self.driver)
                        action.move_to_element(random_element).perform()
                        time.sleep(random.uniform(0.5, 1.5))
                except:
                    pass
            
            print("✓ Human behavior simulation complete")
            
        except Exception as e:
            print(f"Note: Some behavior simulation skipped")
    
    def visit_website(self, url):
        """Visit a website through Tor using browser with realistic human behavior"""
        try:
            if not url.startswith(('http://', 'https://')):
                url = 'https://' + url
            
            print(f"\n🌐 Visiting: {url}")
            
            initial_delay = random.uniform(1.2, 2.8)
            print(f"⏱️  Initial delay: {initial_delay:.1f}s")
            time.sleep(initial_delay)
            
            print("📄 Loading page...")
            self.driver.get(url)
            
            # Inject fingerprint spoofing after page loads
            if hasattr(self, 'current_screen_res'):
                self.inject_fingerprint_spoofing(self.current_screen_res)
            
            wait_time = random.uniform(2.5, 5.0)
            print(f"⏱️  Page load wait: {wait_time:.1f}s")
            time.sleep(wait_time)
            
            try:
                page_title = self.driver.title
                current_url = self.driver.current_url
                print(f"📋 Page Title: {page_title}")
                print(f"🔗 Current URL: {current_url}")
            except:
                pass
            
            self.simulate_human_behavior()
            
            final_pause = random.uniform(1.5, 3.0)
            time.sleep(final_pause)
            
            return True
            
        except Exception as e:
            print(f"❌ Error visiting website: {e}")
            return False
    
    def cleanup(self):
        """Close browser and cleanup"""
        if self.driver:
            self.driver.quit()
            print("✓ Browser closed")
    
    def run(self):
        """Main bot execution"""
        print("=" * 70)
        print("🤖 TOR NETWORK BOT - Advanced Human Behavior Simulation")
        print("=" * 70)
        
        # Ensure Tor is running
        self.ensure_tor_running()
        
        print("\n🔍 Checking Tor connection...")
        current_ip = self.get_current_ip()
        if current_ip:
            print(f"✅ Connected to Tor. Current IP: {current_ip}")
        else:
            print("❌ Failed to connect to Tor network")
            print("Make sure Tor service is running")
            sys.exit(1)
        
        print("\n" + "-" * 70)
        url = input("🔗 Enter website URL to visit: ").strip()
        
        if not url:
            print("❌ No URL provided. Exiting.")
            sys.exit(1)
        
        # Ask user how many visits they want
        while True:
            try:
                num_visits = input("🔢 How many visits do you want? (1-1000): ").strip()
                num_visits = int(num_visits)
                if 1 <= num_visits <= 1000:
                    break
                else:
                    print("⚠️  Please enter a number between 1 and 1000")
            except ValueError:
                print("⚠️  Please enter a valid number")
        
        print("-" * 70)
        
        try:
            print("\n🔧 Setting up browser with randomized fingerprint...")
            if not self.setup_browser():
                print("❌ Failed to setup browser")
                sys.exit(1)
            
            # Track successful and failed visits
            successful_visits = 0
            failed_visits = 0
            
            # Perform the visits
            for visit_num in range(1, num_visits + 1):
                if visit_num > 1:
                    delay = random.uniform(5, 12)
                    print(f"\n⏸️  Simulating user break: {delay:.1f}s...")
                    time.sleep(delay)
                    
                    print("\n🔄 Closing browser to reset fingerprint...")
                    self.cleanup()
                    time.sleep(random.uniform(2, 4))
                    
                    print("\n" + "=" * 70)
                    print("🔄 Requesting new Tor circuit and fresh identity...")
                    print("=" * 70)
                    if self.renew_tor_ip():
                        current_ip = self.get_current_ip()
                        print(f"✅ New IP: {current_ip}")
                    
                    print("\n🔧 Setting up new browser with different fingerprint...")
                    if not self.setup_browser():
                        print("❌ Failed to setup browser")
                        failed_visits += 1
                        print(f"❌ Visit {visit_num}/{num_visits} FAILED - Browser setup error")
                        continue
                    
                    delay = random.uniform(3, 7)
                    print(f"\n⏱️  Waiting {delay:.1f}s before visiting...")
                    time.sleep(delay)
                
                print(f"\n" + "=" * 70)
                print(f"🌍 [VISIT {visit_num}/{num_visits}] Using IP: {current_ip}")
                print("=" * 70)
                
                # Visit website and track success
                visit_success = self.visit_website(url)
                if visit_success:
                    successful_visits += 1
                    print(f"✅ Visit {visit_num}/{num_visits} SUCCESSFUL")
                else:
                    failed_visits += 1
                    print(f"❌ Visit {visit_num}/{num_visits} FAILED")
            
            final_delay = random.uniform(3, 6)
            print(f"\n⏸️  Final delay: {final_delay:.1f}s")
            time.sleep(final_delay)
            
            print("\n" + "=" * 70)
            print("✅ Bot execution completed")
            print("=" * 70)
            print("\n📊 Summary:")
            print(f"   • Total visits attempted: {num_visits}")
            print(f"   • Successful visits: {successful_visits} ✅")
            print(f"   • Failed visits: {failed_visits} ❌")
            print(f"   • Success rate: {(successful_visits/num_visits*100):.1f}%")
            print(f"   • Each visit used different IP and browser fingerprint")
            print(f"   • Human-like behavior simulated throughout")
            print("=" * 70)
            
        finally:
            self.cleanup()


if __name__ == "__main__":
    bot = TorBot()
    bot.run()
