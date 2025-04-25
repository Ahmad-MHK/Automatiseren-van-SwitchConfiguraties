# Network Automation Script

Automatiseer het configureren van meerdere netwerk switches via SSH, met logging, configuratiebestanden, cooldown-timers en veilige opslag van wachtwoorden via `.env`.

---

## 📦 Projectstructuur

```bash
network_automation_project/
│
├── .env                      # Bevat je gebruikersnaam en wachtwoord (NOOIT uploaden)
├── config_files/             # Hier bewaar je configuratiebestanden (bv. voor interfaces)
│   └── example_config.txt
├── device_data/              # Lijst van switches met IP en type
│   └── devices.json
├── logs/                     # Bevat automatisch gegenereerde logbestanden
├── send_config.py            # Het hoofdscript
├── requirements.txt          # Benodigde Python-pakketten
└── README.md                 # Deze uitleg
