from flask import Flask, render_template, request, redirect, url_for
import os
import time
import paramiko
import telnetlib

app = Flask(__name__)

# =================== Folder Configuration ===================

# Define paths for uploading different types of files
app.config["UPLOAD_FOLDER"] = {
    "devices": "Devices",  # Folder containing device definitions
    "configs": "Config"    # Folder containing configuration scripts
}

DEVICES_FOLDER = app.config["UPLOAD_FOLDER"]["devices"]
CONFIG_FOLDER = app.config["UPLOAD_FOLDER"]["configs"]

# =================== Device Parsing ===================

def get_device_entries():
    """Parses device files to extract IP, username, and password information."""
    entries = []
    for file in os.listdir(DEVICES_FOLDER):  # Iterate over all device files
        path = os.path.join(DEVICES_FOLDER, file)
        with open(path) as f:
            lines = [line.strip() for line in f if line.strip()]
            ip = lines[0]  # First line is assumed to be the IP address
            username = None
            password = None
            for line in lines[1:]:
                if line.lower().startswith("username:"):
                    username = line.split(":", 1)[1].strip()
                elif line.lower().startswith("password:"):
                    password = line.split(":", 1)[1].strip()
            entries.append({
                "id": f"{file} - {ip}",       # Unique identifier
                "file": file,                 # File name
                "ip": ip,                     # IP address
                "username": username,
                "password": password,
                "has_password": bool(password),
                "label": f"{ip} [{'password' if password else 'no password'}]"
            })
    return entries

# =================== Config Loading ===================

def load_config_files():
    """Lists all config files in the config folder."""
    return [f for f in os.listdir(CONFIG_FOLDER) if os.path.isfile(os.path.join(CONFIG_FOLDER, f))]

def load_config(filename):
    """Loads the configuration commands from a specified file."""
    with open(os.path.join(CONFIG_FOLDER, filename)) as f:
        return [line.strip() for line in f if line.strip()]

# =================== SSH / Telnet Core ===================

def send_ssh(ip, config_lines, cooldown, username, password):
    """
    Sends configuration lines to a device over SSH.
    Includes basic login check and optional banner scan.
    Note: ERS switches do not support full config mode over SSH.
    """
    output = []
    try:
        from paramiko.transport import Transport

        # Enable support for legacy encryption for ERS devices
        Transport._preferred_kex = ['diffie-hellman-group1-sha1', 'diffie-hellman-group14-sha1']
        Transport._preferred_ciphers = ('aes128-cbc', '3des-cbc', 'aes192-cbc', 'aes256-cbc')

        # Create SSH transport session
        transport = Transport((ip, 22))
        transport.start_client(timeout=10)
        transport.auth_password(username, password)

        # Verify authentication
        if not transport.is_authenticated():
            return f"[✗] SSH login failed for {ip} (invalid credentials?)"

        # Open interactive shell
        session = transport.open_session()
        session.get_pty()
        session.invoke_shell()
        time.sleep(1)

        # Try to read welcome banner (if any)
        try:
            banner = session.recv(1024).decode("utf-8", errors="ignore")
            if "Ctrl-Y" in banner or "Ctrl-Y to begin" in banner:
                session.send("\x19\n")  # Attempt Ctrl+Y (usually doesn't work over SSH on ERS)
                output.append("Sent: Ctrl+Y (SSH attempt)")
                time.sleep(1)
        except:
            pass  # Safe to skip banner read if not supported

        # Attempt to enter config mode (ERS may silently block this)
        session.send("disable clipaging\n")
        time.sleep(0.5)

        for line in config_lines:
            session.send(line + "\n")
            output.append(f"Sent: {line}")
            time.sleep(cooldown)

        session.send("save config\n")
        time.sleep(1)
        session.send("exit\n")

        transport.close()

        return "\n".join(output) + f"\n[✓] SSH config sent successfully to {ip}"

    except Exception as e:
        return f"[✗] SSH error for {ip}: {e}"

def send_telnet(ip, config_lines, cooldown, username, password):
    """
    Sends configuration lines to a device over Telnet.
    Detects if Ctrl+Y is needed based on the login banner.
    """
    output = []
    try:
        tn = telnetlib.Telnet(ip, timeout=10)

        # Read welcome banner and check if Ctrl+Y is required
        banner = tn.read_until(b":", timeout=5)
        if b"Ctrl-Y" in banner or b"Ctrl-Y to begin" in banner:
            tn.write(b"\x19\n")  # Send Ctrl+Y
            output.append("Sent: Ctrl+Y (auto-detected)")
            time.sleep(1)

        # Now proceed with login
        if username:
            tn.read_until(b"Username:", timeout=5)
            tn.write(username.encode("ascii") + b"\n")

        if password:
            tn.read_until(b"Password:", timeout=5)
            tn.write(password.encode("ascii") + b"\n")

        # Enter enable mode and disable paging
        tn.write(b"enable\n")
        if password:
            tn.write(password.encode("ascii") + b"\n")
        tn.write(b"disable clipaging\n")
        time.sleep(1)

        # Send commands
        for line in config_lines:
            tn.write(line.encode("ascii") + b"\n")
            output.append(f"Sent: {line}")
            time.sleep(cooldown)

        tn.write(b"save config\n")
        tn.write(b"exit\n")

        return "\n".join(output) + f"\n[✓] Telnet config sent successfully to {ip}"

    except Exception as e:
        return f"[✗] Telnet error for {ip}: {e}"

# =================== Routes ===================

@app.route("/", methods=["GET", "POST"])
def index():
    """
    Home page: displays available devices and configs.
    Handles POST requests to send configs to selected devices.
    """
    devices = get_device_entries()
    configs = load_config_files()
    result = ""

    if request.method == "POST" and "send_config" in request.form:
        selected_ids = request.form.getlist("devices")          # Devices selected by checkbox
        config_file = request.form["config"]                    # Selected config file
        protocol = request.form["protocol"]                     # ssh or telnet
        cooldown = float(request.form["cooldown"]) / 1000.0     # Convert ms to seconds

        selected_devices = [d for d in devices if d["id"] in selected_ids]
        config_lines = load_config(config_file)

        results = []
        for device in selected_devices:
            if protocol == "ssh":
                r = send_ssh(device["ip"], config_lines, cooldown, device["username"], device["password"])
            else:
                r = send_telnet(device["ip"], config_lines, cooldown, device["username"], device["password"])
            results.append(f"{device['label']}:\n{r}\n")

        result = "\n\n".join(results)

        # Save to logs folder with timestamp
        timestamp = time.strftime("%Y-%m-%d_%H-%M-%S")
        log_filename = f"logs/log_{timestamp}.txt"
        os.makedirs("logs", exist_ok=True)
        with open(log_filename, "w", encoding="utf-8") as log_file:
            log_file.write(result)



    return render_template("index.html", devices=devices, configs=configs, result=result)

@app.route("/upload", methods=["POST"])
def upload_file():
    """
    Uploads a device or config file to the appropriate folder.
    """
    file = request.files["file"]
    filetype = request.form["filetype"]
    if file and filetype in app.config["UPLOAD_FOLDER"]:
        path = os.path.join(app.config["UPLOAD_FOLDER"][filetype], file.filename)
        file.save(path)
    return redirect(url_for("index"))

@app.route("/delete", methods=["POST"])
def delete_file():
    """
    Deletes a device or config file by name.
    """
    filename = request.form["filename"]
    filetype = request.form["filetype"]
    folder = app.config["UPLOAD_FOLDER"][filetype]
    path = os.path.join(folder, filename)
    if os.path.exists(path):
        os.remove(path)
    return redirect(url_for("index"))

@app.route("/logs")
def show_logs():
    """Lists and displays all saved log files."""
    log_files = sorted(os.listdir("logs"), reverse=True)
    logs = []
    for file in log_files:
        path = os.path.join("logs", file)
        with open(path) as f:
            logs.append((file, f.read()))
    return render_template("logs.html", logs=logs)


if __name__ == "__main__":
    app.run(debug=True)
