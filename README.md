# Switch Config Tool

A web-based tool to push configurations to network switches via SSH or Telnet.

---

## Features

* Upload device connection profiles (IP, optional username/password)
* Upload configuration files (text-based command sets)
* Select one or more devices to push config to
* Choose protocol: SSH or Telnet
* Customize command cooldown (in milliseconds)
* View success/failure feedback per device
* Web interface with upload and delete functionality
* Clean UI with logo and credit footer

---

## Folder Structure

```
project/
├── app.py
├── Devices/              # Device IP files (one per file)
├── Config/               # CLI config files
├── static/
│   ├── style.css         # UI styling
│   └── logo.png          # Your logo (optional)
├── templates/
│   └── index.html        # Web interface template
```

---

## Device File Format (in /Devices)

```
192.168.1.1
username:admin
password:admin123
```

* Only IP is required
* Username/password are optional

---

## Config File Format (in /Config)

```
configure terminal
interface ethernet 1/1
description TEST-CONFIG-FROM-SCRIPT
exit
exit
```

---

## Running Locally

### Install Requirements

```bash
pip install flask paramiko
```

### Start the App

```bash
python app.py
```

Then open:

```
http://localhost:5000
```

---

## Deployment (Unix server)

Later, you can use `gunicorn` + `nginx` to run this as a secure service.

---

## Credits

Made by **Ahmad Mahouk**
