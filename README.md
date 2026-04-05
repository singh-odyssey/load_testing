# IP Routing & Engagement Toolkit

A comprehensive toolkit for Tor-routed network testing, featuring both high-intensity load testing and realistic browser simulation.

**⚠️ WARNING: This tool is for testing YOUR OWN applications only. Unauthorized use against websites you do not own is illegal and can have severe consequences.**

---

## 🛠️ Installation

Run the setup script to install all dependencies (Tor, Firefox, Geckodriver, Python requirements) and configure the environment.

```bash
chmod +x setup.sh
./setup.sh
```

---

## 🚀 Mode 1: High-Intensity Load Testing
*Best for: Stress testing, load generation, checking server resilience.*

This mode uses lightweight HTTP requests to generate significant traffic. **Warning:** `boom.py` is capable of generating traffic levels comparable to a Distributed Denial of Service (DDoS) attack.

### 1. Basic Usage (`boom.py`)
Run the load tester directly in interactive mode. This is the easiest way to start a single test.

```bash
python3 boom.py
```
*Prompts for target URL, anonymity mode (Tor/Proxy/Direct), and other settings.*

### 2. Persistent Mode (`run.sh`)
Runs the bot with a **watchdog** that automatically restarts it if it crashes or stops. Ideal for long-running tests.

```bash
chmod +x run.sh
./run.sh
```
*Prompts for target URL and runs continuously.*

### 3. Swarm Mode (`start_swarm.sh`)
Launches **multiple bot instances** in the background using `tmux`. Each instance runs in its own watchdog loop.

```bash
chmod +x start_swarm.sh
./start_swarm.sh
```
*Prompts for target URL, number of bots, and anonymity mode.*

**Managing the Swarm:**
- **View bots:** `tmux attach -t bot_swarm`
- **Detach:** `Ctrl+B`, then `D`
- **Stop all:** `tmux kill-session -t bot_swarm`

---

## 🌐 Mode 2: Browser Simulation (`tor_bot.py`)
*Best for: Engagement simulation, testing fingerprinting defenses, realistic user behavior.*

This mode uses **Selenium with Firefox** to simulate real user interactions. It features:
- **Advanced Fingerprinting**: Randomizes User-Agent, Screen Resolution, and more.
- **Tor IP Rotation**: Requests a new Tor circuit for every visit.
- **Human Behavior**: Simulates mouse movements, scrolling, and random delays.

### Usage

```bash
python3 tor_bot.py
```

The script will interactively ask for:
1.  **Target URL**: The website to visit.
2.  **Number of Visits**: How many unique sessions to generate.

---

## 📂 File Structure

- **`boom.py`**: Core logic for the HTTP load testing bot.
- **`tor_bot.py`**: Core logic for the Selenium browser bot.
- **`run.sh`**: Watchdog script for `boom.py`.
- **`start_swarm.sh`**: Swarm manager for multiple `run.sh` instances.
- **`setup.sh`**: Automated installation and configuration script.
- **`dashboard.py`**: (Optional) Visualization tool for bot statistics.

