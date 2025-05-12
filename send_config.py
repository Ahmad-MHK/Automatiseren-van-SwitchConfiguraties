import paramiko
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

def send_config_ssh(ip, config_lines, cooldown, username=None, password=None):
    try:
        print(f"\n[+] Connecting to {ip} via SSH...")

        from paramiko.transport import Transport
        Transport._preferred_kex = [
            'diffie-hellman-group1-sha1',
            'diffie-hellman-group14-sha1'
        ]
        Transport._preferred_ciphers = (
            'aes128-cbc',
            '3des-cbc',
            'aes192-cbc',
            'aes256-cbc'
        )

        transport = Transport((ip, 22))
        transport.start_client(timeout=10)
        transport.auth_password(username, password)

        if not transport.is_authenticated():
            raise Exception("SSH authentication failed.")

        session = transport.open_session()
        session.get_pty()
        session.invoke_shell()
        time.sleep(1)

        session.send("disable clipaging\n")
        time.sleep(0.5)

        for line in config_lines:
            session.send(line + "\n")
            time.sleep(cooldown)

        session.send("save config\n")
        time.sleep(1)
        session.send("exit\n")

        transport.close()
        print(f"[✓] Config sent to {ip} successfully.")
    except Exception as e:
        print(f"[✗] Failed to connect/send to {ip} via SSH: {e}")

def send_config_telnet(ip, config_lines, cooldown, username=None, password=None):
    try:
        print(f"\n[+] Connecting to {ip} via Telnet...")
        tn = telnetlib.Telnet(ip, timeout=10)

        if username:
            tn.read_until(b"Username: ")
            tn.write(username.encode("ascii") + b"\n")

        if password:
            tn.read_until(b"Password: ")
            tn.write(password.encode("ascii") + b"\n")

        tn.write(b"enable\n")
        if password:
            tn.write(password.encode("ascii") + b"\n")

        tn.write(b"disable clipaging\n")
        time.sleep(1)

        for line in config_lines:
            tn.write(line.encode("ascii") + b"\n")
            time.sleep(cooldown)

        tn.write(b"save config\n")
        tn.write(b"exit\n")
        print(f"[✓] Telnet config sent to {ip} successfully.")
    except Exception as e:
        print(f"[✗] Failed to connect/send to {ip} via Telnet: {e}")

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

    protocol = input("Choose protocol (ssh/telnet): ").strip().lower()
    if protocol not in ("ssh", "telnet"):
        print("Invalid protocol. Must be 'ssh' or 'telnet'.")
        return

    for device in selected_devices:
        if protocol == "ssh":
            send_config_ssh(device['ip'], config_lines, cooldown, device['username'], device['password'])
        else:
            send_config_telnet(device['ip'], config_lines, cooldown, device['username'], device['password'])

if __name__ == "__main__":
    main()
