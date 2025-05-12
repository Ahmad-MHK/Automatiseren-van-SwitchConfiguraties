import telnetlib
import time
import os

DEVICES_FOLDER = "Devices"
CONFIG_FOLDER = "Config"

def get_device_entries():
    entries = []
    for file in os.listdir(DEVICES_FOLDER):
        path = os.path.join(DEVICES_FOLDER, file)
        with open(path) as f:
            lines = [line.strip() for line in f if line.strip()]
            ip = lines[0]
            username = None
            password = None
            for line in lines[1:]:
                if line.lower().startswith("username:"):
                    username = line.split(":", 1)[1].strip()
                elif line.lower().startswith("password:"):
                    password = line.split(":", 1)[1].strip()
            entries.append({"ip": ip, "username": username, "password": password})
    return entries

def list_config_files():
    return [f for f in os.listdir(CONFIG_FOLDER) if os.path.isfile(os.path.join(CONFIG_FOLDER, f))]

def load_config(filename):
    with open(os.path.join(CONFIG_FOLDER, filename)) as f:
        return [line.strip() for line in f if line.strip()]

def send_config(ip, config_lines, cooldown, username=None, password=None):
    try:
        print(f"\nConnecting to {ip}...")
        tn = telnetlib.Telnet(ip, timeout=10)

        if username and password:
            tn.read_until(b"Username: ", timeout=5)
            tn.write(username.encode('ascii') + b"\n")
            tn.read_until(b"Password: ", timeout=5)
            tn.write(password.encode('ascii') + b"\n")

        tn.write(b"enable\n")
        if password:
            tn.write(password.encode('ascii') + b"\n")

        tn.write(b"terminal length 0\n")

        for line in config_lines:
            tn.write(line.encode("ascii") + b"\n")
            time.sleep(cooldown)

        tn.write(b"end\n")
        tn.write(b"exit\n")
        print(f"Config sent to {ip} successfully.")
    except Exception as e:
        print(f"Failed to connect/send to {ip}: {e}")

def main():
    all_devices = get_device_entries()
    all_ips = [d['ip'] for d in all_devices]

    print("\nAvailable devices:")
    for i, ip in enumerate(all_ips):
        print(f"{i + 1}. {ip}")
    
    choice = input("\nChoose device number (or type 'all'): ").strip()
    if choice.lower() == 'all':
        selected_devices = all_devices
    else:
        try:
            index = int(choice) - 1
            selected_devices = [all_devices[index]]
        except:
            print("Invalid selection.")
            return

    configs = list_config_files()
    print("\nAvailable config files:")
    for i, fname in enumerate(configs):
        print(f"{i + 1}. {fname}")

    try:
        config_choice = int(input("Choose config number: ")) - 1
        config_lines = load_config(configs[config_choice])
    except:
        print("Invalid config choice.")
        return

    try:
        cooldown = float(input("Enter cooldown (seconds) between commands: "))
    except:
        print("Invalid cooldown.")
        return

    for device in selected_devices:
        send_config(device['ip'], config_lines, cooldown, device['username'], device['password'])

if __name__ == "__main__":
    main()
