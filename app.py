from flask import Flask, render_template, request, redirect, url_for
import os
import time
import paramiko
import telnetlib

app = Flask(__name__)
app.config["UPLOAD_FOLDER"] = {
    "devices": "Devices",
    "configs": "Config"
}

DEVICES_FOLDER = app.config["UPLOAD_FOLDER"]["devices"]
CONFIG_FOLDER = app.config["UPLOAD_FOLDER"]["configs"]

# =================== Device Parsing ===================

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
            entries.append({
                "id": f"{file} - {ip}",
                "file": file,
                "ip": ip,
                "username": username,
                "password": password,
                "has_password": bool(password),
                "label": f"{ip} [{'password' if password else 'no password'}]"
            })
    return entries

def load_config_files():
    return [f for f in os.listdir(CONFIG_FOLDER) if os.path.isfile(os.path.join(CONFIG_FOLDER, f))]

def load_config(filename):
    with open(os.path.join(CONFIG_FOLDER, filename)) as f:
        return [line.strip() for line in f if line.strip()]

# =================== SSH / Telnet Core ===================

def send_ssh(ip, config_lines, cooldown, username, password):
    output = []
    try:
        from paramiko.transport import Transport
        Transport._preferred_kex = ['diffie-hellman-group1-sha1', 'diffie-hellman-group14-sha1']
        Transport._preferred_ciphers = ('aes128-cbc', '3des-cbc', 'aes192-cbc', 'aes256-cbc')

        transport = Transport((ip, 22))
        transport.start_client(timeout=10)
        transport.auth_password(username, password)

        if not transport.is_authenticated():
            return "SSH authentication failed."

        session = transport.open_session()
        session.get_pty()
        session.invoke_shell()
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
        return "\n".join(output) + "\n[✓] SSH config sent successfully."
    except Exception as e:
        return f"[✗] SSH error: {e}"

def send_telnet(ip, config_lines, cooldown, username, password):
    output = []
    try:
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
            output.append(f"Sent: {line}")
            time.sleep(cooldown)

        tn.write(b"save config\n")
        tn.write(b"exit\n")
        return "\n".join(output) + "\n[✓] Telnet config sent successfully."
    except Exception as e:
        return f"[✗] Telnet error: {e}"

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
        cooldown = float(request.form["cooldown"]) / 1000.0  # convert ms to seconds

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
    folder = app.config["UPLOAD_FOLDER"][filetype]
    path = os.path.join(folder, filename)
    if os.path.exists(path):
        os.remove(path)
    return redirect(url_for("index"))

if __name__ == "__main__":
    app.run(debug=True)
