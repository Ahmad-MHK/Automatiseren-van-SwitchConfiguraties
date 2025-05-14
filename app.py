from flask import Flask, render_template, request, redirect, url_for
import os, time, re
import paramiko, telnetlib

app = Flask(__name__)

# =================== Folder Configuration ===================
app.config["UPLOAD_FOLDER"] = {
    "devices": "Devices",
    "configs": "Config"
}

DEVICES_FOLDER = app.config["UPLOAD_FOLDER"]["devices"]
CONFIG_FOLDER = app.config["UPLOAD_FOLDER"]["configs"]

# =================== Utility Functions ===================
def slugify(text):
    return re.sub(r'\W+', '_', text)

def get_device_entries():
    entries = []
    for file in os.listdir(DEVICES_FOLDER):
        path = os.path.join(DEVICES_FOLDER, file)
        with open(path) as f:
            lines = [line.strip() for line in f if line.strip()]
            ip = lines[0]
            username = password = None
            variables = {}

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

def load_config_files():
    return [f for f in os.listdir(CONFIG_FOLDER) if os.path.isfile(os.path.join(CONFIG_FOLDER, f))]

def load_config(filename):
    with open(os.path.join(CONFIG_FOLDER, filename)) as f:
        return [line.strip() for line in f if line.strip()]

def replace_config_vars(line, vars_dict):
    for key, val in vars_dict.items():
        line = line.replace(key, val)
    return line

# =================== SSH / Telnet ===================
def send_ssh(ip, config_lines, cooldown, username, password):
    import paramiko
    output = []

    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(ip, username=username, password=password, timeout=10, look_for_keys=False)

        chan = ssh.invoke_shell()
        time.sleep(1)
        banner = chan.recv(1024).decode("utf-8", errors="ignore")

        if "Ctrl-Y" in banner or "Ctrl-Y to begin" in banner:
            chan.send("\x19\n")
            output.append("Sent: Ctrl+Y (auto-detected in SSH)")
            time.sleep(1)

        chan.send("disable clipaging\n")
        time.sleep(0.5)

        for line in config_lines:
            chan.send(line + "\n")
            output.append(f"Sent: {line}")
            time.sleep(cooldown)

        chan.send("save config\n")
        chan.send("exit\n")

        ssh.close()
        return "\n".join(output) + f"\n[✓] SSH config sent to {ip}"

    except Exception as e:
        return f"[✗] SSH error for {ip}: {e}"

def send_telnet(ip, config_lines, cooldown, username, password):
    output = []
    try:
        tn = telnetlib.Telnet(ip, timeout=10)
        try:
            banner = tn.read_until(b":", timeout=5)
            if b"Ctrl-Y" in banner:
                tn.write(b"\x19\n")
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
        return "\n".join(output) + f"\n[\u2713] Telnet config sent to {ip}"
    except Exception as e:
        return f"[\u2717] Telnet error for {ip}: {e}"

# =================== Routes ===================
@app.route("/", methods=["GET", "POST"])
def index():
    devices = get_device_entries()
    configs = load_config_files()
    result = ""

    if request.method == "POST" and "send_config" in request.form:
        selected_ids = request.form.getlist("devices")
        config_file = request.form["config"]
        protocol = request.form["protocol"]
        cooldown = float(request.form["cooldown"]) / 1000.0

        selected_devices = [d for d in devices if d["id"] in selected_ids]
        config_lines = load_config(config_file)

        results = []
        for device in selected_devices:
            vars_for_device = device.get("variables", {}).copy()
            form_vars = extract_device_vars(request.form, device["form_id"])
            vars_for_device.update(form_vars)

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

    return render_template("index.html", devices=devices, configs=configs, result=result)

@app.route("/upload", methods=["POST"])
def upload_file():
    file = request.files["file"]
    filetype = request.form["filetype"]
    if file and filetype in app.config["UPLOAD_FOLDER"]:
        path = os.path.join(app.config["UPLOAD_FOLDER"][filetype], file.filename)
        file.save(path)
    return redirect(url_for("index"))

@app.route("/delete", methods=["POST"])
def delete_file():
    filename = request.form["filename"]
    filetype = request.form["filetype"]
    path = os.path.join(app.config["UPLOAD_FOLDER"][filetype], filename)
    if os.path.exists(path):
        os.remove(path)
    return redirect(url_for("index"))

@app.route("/logs")
def show_logs():
    files = sorted(os.listdir("logs"), reverse=True)
    logs = [(f, open(os.path.join("logs", f)).read()) for f in files]
    return render_template("logs.html", logs=logs)

@app.route("/test-send", methods=["POST"])
def test_send():
    result = send_telnet("192.168.1.1", ["enable", "conf t", "exit"], 0.5, None, None)
    return render_template("index.html", devices=get_device_entries(), configs=load_config_files(), result="(TEST)\n" + result)

if __name__ == "__main__":
    app.run(debug=True)
