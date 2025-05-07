import os
import json
import time
import logging
import socket
import argparse
from datetime import datetime
from netmiko import ConnectHandler, NetMikoTimeoutException, NetMikoAuthenticationException

# === Argumenten verwerken ===
parser = argparse.ArgumentParser(description="Switch configuratie tool")
parser.add_argument("--show", action="store_true", help="Toon verificatie na configuratie")
args = parser.parse_args()

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

console = logging.StreamHandler()
console.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(message)s', datefmt='%H:%M:%S')
console.setFormatter(formatter)
logging.getLogger().addHandler(console)

# === Laad apparatenlijst uit JSON ===
with open("device_data/devices.json", "r") as f:
    devices = json.load(f)

# Toon beschikbare switches
print("Beschikbare switches:")
for idx, device in enumerate(devices, start=1):
    print(f"{idx}. {device['name']} ({device['ip']})")

print("0. Alle switches")

# === Gebruiker laat switch kiezen ===
try:
    selected_index = int(input("Selecteer een switch (nummer, of 0 voor alle): "))
    if selected_index == 0:
        selected_devices = devices  # Alle apparaten selecteren
    else:
        selected_devices = [devices[selected_index - 1]]
except (IndexError, ValueError):
    print("Ongeldige selectie.")
    exit()

# === Gebruiker kiest SSH of Telnet ===
try:
    port_choice = int(input("Kies protocol:\n22 = SSH\n23 = Telnet\nKeuze: ").strip())
    if port_choice not in [22, 23]:
        print("Ongeldige keuze, standaard naar poort 22 (SSH).")
        port_choice = 22
except ValueError:
    print("Ongeldige invoer, standaard naar poort 22 (SSH).")
    port_choice = 22

# === Configbestand kiezen ===
config_name = input("Naam van configbestand in 'config_files/' (bijv. example_config.txt): ").strip()
config_path = os.path.join("config_files", config_name)

if not os.path.exists(config_path):
    print("Configbestand niet gevonden.")
    exit()

# === Cooldown instellen ===
try:
    cooldown_ms = int(input("Cooldown in milliseconden: ").strip())
    cooldown = cooldown_ms / 1000
except ValueError:
    print("Ongeldige cooldown ingevoerd.")
    exit()

# === TCP verbinding testen vóór poging tot login ===
def check_connection(ip, port=22, timeout=5):
    try:
        with socket.create_connection((ip, port), timeout=timeout):
            return True
    except (socket.timeout, socket.error):
        return False

# === Itereer over geselecteerde switches ===
for selected_device in selected_devices:
    print(f"\n--- Verwerken: {selected_device['name']} ({selected_device['ip']}) ---")

    if not check_connection(selected_device['ip'], port_choice):
        print(f"Kan geen verbinding maken met {selected_device['ip']} op poort {port_choice}.")
        logging.error(f"Kan geen verbinding maken met {selected_device['ip']} op poort {port_choice}.")
        continue
    else:
        print(f"TCP verbinding naar {selected_device['ip']} op poort {port_choice} succesvol.")
        logging.info(f"TCP verbinding naar {selected_device['ip']} op poort {port_choice} succesvol.")

    # === Verbindingsinstellingen voorbereiden ===
    switch = {
        'host': selected_device['ip'],
        'port': port_choice
    }

    if port_choice == 22:
        switch['device_type'] = selected_device['device_type']
    elif port_choice == 23:
        switch['device_type'] = 'cisco_ios_telnet'
        print("Telnet modus actief.")

    if 'username' in selected_device and 'password' in selected_device:
        switch['username'] = selected_device['username']
        switch['password'] = selected_device['password']
        logging.info("Inloggen met gebruikersnaam en wachtwoord.")
    else:
        if port_choice == 23:
            switch['username'] = ''
            switch['password'] = ''
            switch['default_enter'] = '\r'
            switch['session_log'] = 'telnet_session.log'
            logging.info("Telnet zonder username/password ingesteld.")
        else:
            logging.info("Inloggen zonder gebruikersnaam/wachtwoord (anoniem of SSH keys).")

    # === Configuratie verzenden en eventueel controleren ===
    try:
        with open(config_path, 'r') as f:
            commands = f.read().splitlines()

        print(f"Verbinden met {switch['host']} ({selected_device['name']}) op poort {port_choice}...")
        net_connect = ConnectHandler(**switch)

        print("Configuratie versturen...")
        output = net_connect.send_config_set(commands)
        print(output)

        if args.show:
            print("Verificatie uitvoeren...")
            try:
                verify = net_connect.send_command("show running-config | include hostname")
                print("Verificatie output:")
                print(verify)
                logging.info(f"Verificatie output: {verify}")
            except Exception as e:
                print(f"Verificatie mislukt: {e}")
                logging.warning(f"Verificatie mislukt: {e}")

        net_connect.disconnect()
        print(f"Configuratie verzonden. Wachten {cooldown_ms} ms...")
        time.sleep(cooldown)

    except (NetMikoTimeoutException, NetMikoAuthenticationException) as e:
        print(f"Verbindingsfout tijdens verbinding: {e}")
        logging.error(f"Verbindingsfout tijdens verbinding: {e}")
    except Exception as e:
        print(f"Er is een fout opgetreden: {e}")
        logging.error(f"Algemene fout: {e}")

    logging.info(f"Gebruik configbestand: {config_name}")


# === Mad by Ahmad Mahouk Software developer ===
