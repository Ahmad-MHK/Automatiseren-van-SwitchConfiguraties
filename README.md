# 🔧 Switch Config Deployment Tool

A web-based Python/Flask tool for pushing configuration commands to multiple network switches  via SSH or Telnet. Includes bulk selection, filtering, logging, and upload/delete management of device and config files.

---

## 📦 Features

- ✅ Push configuration to one or many switches (SSH/Telnet)
- ✅ Auto-detect password-protected devices
- ✅ Filter by IP, password presence, or both
- ✅ View and search historical logs in browser
- ✅ Upload/delete config and device files
- ✅ Logs saved per session in `logs/` folder
- ✅ Designed for legacy switch support (e.g., Ctrl+Y detection, legacy ciphers)

---

## 📁 Folder Structure

project/
│
├── app.py # Main Flask app
├── Devices/ # Device files (IP, optional username/password)
├── Config/ # Config scripts (plain text commands)
├── logs/ # Saved logs (auto-created)
├── templates/
│ ├── index.html # Main web UI
│ └── logs.html # Log viewer page
└── static/
├── style.css # Basic styling
└── Com1-Oranje.png # Logo


---

## 🖥️ Device File Format

**With password:**
192.168.1.1
username:admin
password:MySecurePass123

**Without password:**

192.168.1.2


Place these files inside the `Devices/` folder.

---

## ⚙️ Usage

1. Install requirements:
    ```bash
    pip install flask paramiko
    ```

2. Run the server:
    ```bash
    python app.py
    ```

3. Open your browser:
    ```
    http://localhost:5000
    ```

---

## 📄 Logs

- Logs are saved as `.txt` files in the `logs/` folder with timestamped names.
- Accessible via the **"View Logs"** button in the web interface.

---

## 🧠 Known Limitations

- Assumes `disable clipaging` is supported by the device.
- SSH over legacy switches may require relaxed security (handled via Paramiko settings).
- Only CLI/ASCII configs are supported.

---

## 🙋‍♂️ Author

Made with 💡 by **Ahmad Mahouk**  
For Com1 IT Solutions Internship Project


