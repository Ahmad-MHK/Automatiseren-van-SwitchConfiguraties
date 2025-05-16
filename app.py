# Imports and setup
from flask import Flask, render_template, request, redirect, url_for, flash
import os, time, re
import paramiko, telnetlib
from werkzeug.utils import secure_filename
import socket
from paramiko.transport import Transport

# Initialize Flask app
app = Flask(__name__)
app.secret_key = "something-secret"  # Secret key for sessions and flash messages

# Enable detailed Paramiko logging
paramiko.common.logging.basicConfig(level=paramiko.common.DEBUG)

# Folder configuration for uploads
app.config["UPLOAD_FOLDER"] = {
    "devices": "Devices",
    "configs": "Config"
}

# Folder path constants
DEVICES_FOLDER = app.config["UPLOAD_FOLDER"]["devices"]
CONFIG_FOLDER = app.config["UPLOAD_FOLDER"]["configs"]

# Utility: convert device names to safe form field names
def slugify(text):
    return re.sub(r'\W+', '_', text)

# Load device info from files
def get_device_entries():
    entries = []
    for file in os.listdir(DEVICES_FOLDER):
        path = os.path.join(DEVICES_FOLDER, file)
        with open(path) as f:
            lines = [line.strip() for line in f if line.strip()]
            ip = lines[0]
            username = password = None
            variables = {}

            # Parse credentials and variables
            for line in lines[1:]:
                if line.lower().startswith("username:"):
                    username = line.split(":", 1)[1].strip()
                elif line.lower().startswith("password:"):
                    password = line.split(":", 1)[1].strip()
                elif "=" in line:
                    k, v = line.split("=", 1)
                    variables[f"_{k.strip()}_"] = v.strip()

            entries.append({
                "id": f"{file} - {ip}",
                "form_id": slugify(f"{file}_{ip}"),
                "file": file,
                "ip": ip,
                "username": username,
                "password": password,
                "has_password": bool(password),
                "label": f"{ip} [{'password' if password else 'no password'}]",
                "variables": variables
            })
    return entries

# Extract variables submitted from the web form
def extract_device_vars(form, device_form_id):
    result = {}
    prefix = f"var_{device_form_id}_"
    for key in form:
        if key.startswith(prefix) and key.endswith("_key"):
            base = key[:-4]
            var_name = form[key].strip()
            var_value = form.get(base + "_value", "").strip()
            if var_name:
                result[f"_{var_name}_"] = var_value
    return result

# Load config filenames
def load_config_files():
    return [f for f in os.listdir(CONFIG_FOLDER) if os.path.isfile(os.path.join(CONFIG_FOLDER, f))]

# Read config file content
def load_config(filename):
    with open(os.path.join(CONFIG_FOLDER, filename)) as f:
        return [line.strip() for line in f if line.strip()]

# Replace placeholders in config with actual values
def replace_config_vars(line, vars_dict):
    for key, val in vars_dict.items():
        line = line.replace(key, val)
    return line

# Send configuration over SSH to Avaya/ERS device
def send_ssh(ip, config_lines, cooldown, username, password):
    output = []
    try:
        # Set legacy crypto options globally
        Transport._preferred_kex = ['diffie-hellman-group1-sha1', 'diffie-hellman-group14-sha1']
        Transport._preferred_keys = ['ssh-rsa']
        Transport._preferred_macs = ['hmac-sha1', 'hmac-sha1-96', 'hmac-md5', 'hmac-md5-96']
        Transport._preferred_ciphers = ['aes128-cbc', '3des-cbc', 'aes192-cbc', 'aes256-cbc']

        # Establish SSH session
        transport = Transport((ip, 22))
        transport.start_client(timeout=10)
        transport.auth_password(username, password)

        if not transport.is_authenticated():
            return f"[\u2717] SSH login failed for {ip}"

        session = transport.open_session()
        session.get_pty()
        session.invoke_shell()
        time.sleep(1)

        # Required for ERS CLI
        session.send("\x19\n")  # Ctrl+Y
        output.append("Sent: Ctrl+Y to begin session")
        time.sleep(1)

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
        return "\n".join(output) + f"\n[\u2713] SSH config sent successfully to {ip}"

    except Exception as e:
        return f"[\u2717] SSH error for {ip}: {e}"

# Send configuration using Telnet fallback
def send_telnet(ip, config_lines, cooldown, username, password):
    output = []
    try:
        tn = telnetlib.Telnet(ip, timeout=10)

        try:
            banner = tn.read_until(b":", timeout=5)
            if b"Ctrl-Y" in banner:
                tn.write(b"\x19\n")  # Ctrl+Y
                output.append("Sent: Ctrl+Y (auto-detected in Telnet)")
                time.sleep(1)
        except:
            pass

        if username:
            tn.write(username.encode("ascii") + b"\n")
        if password:
            tn.read_until(b"Password:", timeout=5)
            tn.write(password.encode("ascii") + b"\n")

        tn.write(b"enable\n")
        if password:
            tn.write(password.encode("ascii") + b"\n")
        tn.write(b"disable clipaging\n")
        time.sleep(1)

        for line in config_lines:
            tn.write(line.encode("ascii") + b"\n")
            output.append(f"Sent: {line}")
            time.sleep(cooldown)

        tn.write(b"save config\nexit\n")
        return "\n".join(output) + f"\n[+] Telnet config sent to {ip}"
    except Exception as e:
        return f"[X] Telnet error for {ip}: {e}"

# =================== Routes ===================
# Root dashboard
@app.route("/", methods=["GET", "POST"])
def index():
    devices = get_device_entries()
    configs = load_config_files()
    result = ""

    device_files = os.listdir(DEVICES_FOLDER)
    config_files = os.listdir(CONFIG_FOLDER)

    if request.method == "POST" and "send_config" in request.form:
        selected_ids = request.form.getlist("devices")
        config_file = request.form["config"]
        protocol = request.form["protocol"]
        cooldown = float(request.form["cooldown"]) / 1000.0

        selected_devices = [d for d in devices if d["id"] in selected_ids]
        config_lines = load_config(config_file)

        results = []
        for device in selected_devices:
            vars_for_device = extract_device_vars(request.form, device["form_id"])


            replaced_lines = [replace_config_vars(line, vars_for_device) for line in config_lines]

            file_path = os.path.join(DEVICES_FOLDER, device["file"])
            with open(file_path, "w") as f:
                f.write(device["ip"] + "\n")
                if device["username"]:
                    f.write(f"username:{device['username']}\n")
                if device["password"]:
                    f.write(f"password:{device['password']}\n")
                for key, value in vars_for_device.items():
                    stripped = key.strip("_")
                    f.write(f"{stripped}={value}\n")

            if protocol == "ssh":
                out = send_ssh(device["ip"], replaced_lines, cooldown, device["username"], device["password"])
            else:
                out = send_telnet(device["ip"], replaced_lines, cooldown, device["username"], device["password"])

            results.append(f"{device['label']}\n{out}\n")

        result = "\n\n".join(results)
        timestamp = time.strftime("%Y-%m-%d_%H-%M-%S")
        os.makedirs("logs", exist_ok=True)
        with open(f"logs/log_{timestamp}.txt", "w", encoding="utf-8") as f:
            f.write(result)

    return render_template("index.html",
                           devices=devices,
                           configs=configs,
                           result=result,
                           device_files=device_files,
                           config_files=config_files)

# Upload device or config file
@app.route("/upload", methods=["POST"])
def upload_file():
    file = request.files["file"]
    filetype = request.form["filetype"]
    if file and filetype in app.config["UPLOAD_FOLDER"]:
        path = os.path.join(app.config["UPLOAD_FOLDER"][filetype], file.filename)
        file.save(path)
        flash(f"{file.filename} uploaded to {filetype}.")
    return redirect(url_for("index"))

# Delete a device or config file
@app.route("/delete", methods=["POST"])
def delete_file():
    filename = secure_filename(request.form["filename"])
    filetype = request.form["filetype"]
    folder = app.config["UPLOAD_FOLDER"].get(filetype)

    if folder:
        path = os.path.join(folder, filename)
        if os.path.exists(path):
            os.remove(path)
            flash(f"{filename} deleted from {filetype}.")
        else:
            flash(f"{filename} not found.")
    else:
        flash("Invalid file type.")
    return redirect(url_for("index"))

# Show config push logs
@app.route("/logs")
def show_logs():
    files = sorted(os.listdir("logs"), reverse=True)
    logs = [(f, open(os.path.join("logs", f)).read()) for f in files]
    return render_template("logs.html", logs=logs)

# Create a new device manually
@app.route("/create-device", methods=["POST"])
def create_device():
    ip = request.form["ip"].strip()
    username = request.form.get("username", "").strip()
    password = request.form.get("password", "").strip()

    if not ip:
        return redirect(url_for("index"))

    lines = [ip]
    if username:
        lines.append(f"username:{username}")
    if password:
        lines.append(f"password:{password}")

    filepath = os.path.join(DEVICES_FOLDER, f"{ip}.txt")
    with open(filepath, "w") as f:
        f.write("\n".join(lines))

    return redirect(url_for("index"))

# Test config push without logging
@app.route("/test-send", methods=["POST"])
def test_send():
    devices = get_device_entries()
    configs = load_config_files()
    result_lines = []

    selected_ids = request.form.getlist("devices")
    config_file = request.form.get("config")
    protocol = request.form.get("protocol", "telnet")
    cooldown = float(request.form.get("cooldown", 1000)) / 1000.0

    selected_devices = [d for d in devices if d["id"] in selected_ids]

    if not selected_devices:
        return render_template("index.html", devices=devices, configs=configs, result="(TEST) No device selected.", device_files=os.listdir(DEVICES_FOLDER), config_files=os.listdir(CONFIG_FOLDER))
    if not config_file:
        return render_template("index.html", devices=devices, configs=configs, result="(TEST) No config selected.", device_files=os.listdir(DEVICES_FOLDER), config_files=os.listdir(CONFIG_FOLDER))

    config_lines = load_config(config_file)

    for device in selected_devices:
        vars_for_device = device.get("variables", {})
        replaced_lines = [replace_config_vars(line, vars_for_device) for line in config_lines]

        if protocol == "ssh":
            output = send_ssh(device["ip"], replaced_lines, cooldown, device["username"], device["password"])
        else:
            output = send_telnet(device["ip"], replaced_lines, cooldown, device["username"], device["password"])

        result_lines.append(f"(TEST) {device['label']} with config: {config_file}\n{output}")

    return render_template("index.html",
                           devices=devices,
                           configs=configs,
                           result="\n\n".join(result_lines),
                           device_files=os.listdir(DEVICES_FOLDER),
                           config_files=os.listdir(CONFIG_FOLDER))

# Edit config templates
@app.route("/edit-config", methods=["GET", "POST"])
def edit_config():
    configs = load_config_files()
    selected = request.args.get("filename") or request.form.get("filename")
    content = ""

    if request.method == "POST" and selected:
        updated = request.form["content"]
        with open(os.path.join(CONFIG_FOLDER, selected), "w", encoding="utf-8") as f:
            f.write(updated)
        flash(f"{selected} updated successfully.")
        return redirect(url_for("edit_config", filename=selected))

    if selected:
        config_path = os.path.join(CONFIG_FOLDER, selected)
        if os.path.exists(config_path):
            with open(config_path, "r", encoding="utf-8") as f:
                content = f.read()

    return render_template("edit_config.html", configs=configs, selected=selected, content=content)

# Help/documentation page
@app.route("/help")
def help_page():
    return render_template("help.html")

# Save variable values to device files
@app.route("/save-vars", methods=["POST"])
def save_variables():
    devices = get_device_entries()
    selected_ids = request.form.getlist("devices")

    if not selected_ids:
        flash("No devices selected to save variables for.")
        return redirect(url_for("index"))

    for device in devices:
        if device["id"] not in selected_ids:
            continue

        # Extract variables from form for this device
        vars_for_device = extract_device_vars(request.form, device["form_id"])

        # Reconstruct the device file contents
        lines = [device["ip"]]
        if device["username"]:
            lines.append(f"username:{device['username']}")
        if device["password"]:
            lines.append(f"password:{device['password']}")
        for key, value in vars_for_device.items():
            stripped = key.strip("_")
            lines.append(f"{stripped}={value}")

        # Save to file
        file_path = os.path.join(DEVICES_FOLDER, device["file"])
        with open(file_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

    flash("Variables saved successfully for selected devices.")
    return redirect(url_for("index"))

if __name__ == "__main__":
    app.run(debug=True)
