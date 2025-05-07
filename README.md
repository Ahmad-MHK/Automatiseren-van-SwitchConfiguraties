# Switch Configuration Automation

A Python tool for automating configuration deployment to multiple switches via SSH or Telnet, with optional verification.

## 📦 Requirements

* Python 3.8+
* Netmiko
* argparse
* dotenv (optional)

Install dependencies:

```bash
pip install -r requirements.txt
```

## 📁 Project Structure

```
.
├── config_files/         # Your switch configuration files (e.g. example_config.txt)
├── device_data/
│   └── devices.json      # List of switches with IP, type, credentials, etc.
├── logs/                 # Automatically generated logs
├── send_config.py        # Main script
└── README.md
```

## 🧾 Example devices.json

```json
[
  {
    "name": "Switch 1",
    "ip": "192.168.1.1",
    "device_type": "cisco_ios",
    "username": "admin",
    "password": "password"
  },
  {
    "name": "Switch 2",
    "ip": "192.168.1.2",
    "device_type": "extreme_exos"
  }
]
```

## ▶️ How to Use

### Run the script interactively:

```bash
python send_config.py
```

You will be prompted to:

* Select a switch (or "0" for all)
* Choose protocol (22 = SSH, 23 = Telnet)
* Enter config file name from `config_files/`
* Set cooldown in milliseconds between devices

### Optional verification

Use `--show` to run a verification `show` command after applying config:

```bash
python send_config.py --show
```

## ✅ Supported Features

* SSH with or without login
* Telnet with or without login
* Configuration deployment via Netmiko
* Verification using `show running-config`

## 🔒 Safety Notes

* Config is only sent if TCP connection succeeds
* Example configs contain no harmful commands

## 🛠️ Example Config (`example_config.txt`)

```txt
configure terminal
hostname Test-Switch
description VLAN1-Test
disable banner
end
write memory
```

## 📜 Logs

Each run generates a log file in `logs/` named like `log_YYYY-MM-DD_HH-MM-SS.txt`.

---

> Built for automated network switch configuration during internship by **Ahmad Mahouk** 🚀
