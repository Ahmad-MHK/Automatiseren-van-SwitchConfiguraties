import os
import json
import time
import logging
from datetime import datetime
from dotenv import load_dotenv
from netmiko import ConnectHandler

# === Laad .env variabelen ===
load_dotenv()
username = os.getenv("USERNAME")
password = os.getenv("PASSWORD")

# === Logging setup ===
log_dir = "logs"
os.makedirs(log_dir, exist_ok=True)
log_filename = datetime.now().strftime("log_%Y-%m-%d_%H-%M-%S.txt")
log_path = os.path.join(log_dir, log_filename)

logging.basicConfig(
    filename=log_path,
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Ook loggen naar terminal:
console = logging.StreamHandler()
console.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(message)s', datefmt='%H:%M:%S')
console.setFormatter(formatter)
logging.getLogger().addHandler(console)


# === Laad apparaten uit JSON ===
with open("device_data/devices.json", "r") as f:
    devices = json.load(f)

print("Beschikbare switches:")
for idx, device in enumerate(devices, start=1):
    print(f"{idx}. {device['name']} ({device['ip']})")

try:
    selected_index = int(input("Selecteer een switch (nummer): ")) - 1
    selected_device = devices[selected_index]
except (IndexError, ValueError):
    print("Ongeldige selectie.")
    exit()

# === Vraag configuratiebestand op ===
config_name = input("Naam van configbestand in 'config_files/' (bijv. example_config.txt): ").strip()
config_path = os.path.join("config_files", config_name)

if not os.path.exists(config_path):
    print("Configbestand niet gevonden.")
    exit()

# === Vraag cooldown in ms op ===
try:
    cooldown_ms = int(input("Cooldown in milliseconden: ").strip())
    cooldown = cooldown_ms / 1000
except ValueError:
    print("Ongeldige cooldown ingevoerd.")
    exit()

# === Bereid verbinding voor ===
switch = {
    'device_type': selected_device['device_type'],
    'host': selected_device['ip'],
    'username': username,
    'password': password,
}

# === Lees en verstuur configuratie ===
try:
    with open(config_path, 'r') as f:
        commands = f.read().splitlines()

    print(f"Verbinden met {switch['host']} ({selected_device['name']})...")
    net_connect = ConnectHandler(**switch)

    print("Configuratie versturen...")
    output = net_connect.send_config_set(commands)
    print(output)

    net_connect.disconnect()
    print(f"Configuratie verzonden. Wachten {cooldown_ms} ms...")
    time.sleep(cooldown)

except Exception as e:
    print(f"Er is een fout opgetreden: {e}")

logging.info(f"Gebruik configbestand: {config_name}")
