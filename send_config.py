import os
import json
import time
import logging
from datetime import datetime
import socket
from netmiko import ConnectHandler, NetMikoTimeoutException, NetMikoAuthenticationException

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

# Log ook naar console
console = logging.StreamHandler()
console.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(message)s', datefmt='%H:%M:%S')
console.setFormatter(formatter)
logging.getLogger().addHandler(console)

# === Laad apparatenlijst ===
with open("device_data/devices.json", "r") as f:
    devices = json.load(f)

print("Beschikbare switches:")
for idx, device in enumerate(devices, start=1):
    print(f"{idx}. {device['name']} ({device['ip']})")

# === Selectie ===
try:
    selected_index = int(input("Selecteer een switch (nummer): ")) - 1
    selected_device = devices[selected_index]
except (IndexError, ValueError):
    print("Ongeldige selectie.")
    exit()

# === Configbestand kiezen ===
config_name = input("Naam van configbestand in 'config_files/' (bijv. example_config.txt): ").strip()
config_path = os.path.join("config_files", config_name)

if not os.path.exists(config_path):
    print("Configbestand niet gevonden.")
    exit()

# === Cooldown opvragen ===
try:
    cooldown_ms = int(input("Cooldown in milliseconden: ").strip())
    cooldown = cooldown_ms / 1000
except ValueError:
    print("Ongeldige cooldown ingevoerd.")
    exit()

# === Bereid verbindingsgegevens voor ===
switch = {
    'device_type': selected_device['device_type'],
    'host': selected_device['ip'],
}

# Voeg username/password toe als ze bestaan
if 'username' in selected_device and 'password' in selected_device:
    switch['username'] = selected_device['username']
    switch['password'] = selected_device['password']
    logging.info("Inloggen met gebruikersnaam en wachtwoord.")
else:
    logging.info("Inloggen zonder gebruikersnaam/wachtwoord (anoniem of SSH keys).")

# === Verbinding controleren ===
def check_connection(ip, port=22, timeout=5):
    """Controleer of TCP verbinding mogelijk is met de switch."""
    try:
        with socket.create_connection((ip, port), timeout=timeout):
            return True
    except (socket.timeout, socket.error):
        return False

if not check_connection(selected_device['ip']):
    print(f"Kan geen verbinding maken met {selected_device['ip']} op poort 22.")
    logging.error(f"Kan geen verbinding maken met {selected_device['ip']} op poort 22.")
    exit()
else:
    print(f"TCP verbinding naar {selected_device['ip']} succesvol.")
    logging.info(f"TCP verbinding naar {selected_device['ip']} succesvol.")

# === Config versturen ===
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

except (NetMikoTimeoutException, NetMikoAuthenticationException) as e:
    print(f"Verbindingsfout tijdens SSH: {e}")
    logging.error(f"Verbindingsfout tijdens SSH: {e}")
except Exception as e:
    print(f"Er is een fout opgetreden: {e}")
    logging.error(f"Algemene fout: {e}")

logging.info(f"Gebruik configbestand: {config_name}")
