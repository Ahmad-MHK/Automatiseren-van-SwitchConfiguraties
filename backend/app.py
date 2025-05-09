from flask import Flask, request, jsonify
from netmiko import ConnectHandler, NetMikoTimeoutException, NetMikoAuthenticationException
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

@app.route('/api/send-config', methods=['POST'])
def send_config():
    data = request.get_json()

    ip = data.get('ip')
    protocol = data.get('protocol')
    device_type = data.get('deviceType')
    username = data.get('username', '')
    password = data.get('password', '')
    config = data.get('config')

    # Use terminal_server if no login is required for Telnet
    if protocol == 'telnet':
        if not username and not password:
            device_type = 'terminal_server'
        else:
            device_type = 'cisco_ios_telnet'

    device = {
        'device_type': device_type,
        'host': ip,
        'port': 23 if protocol == 'telnet' else 22
    }

    if protocol == 'telnet' and not username and not password:
        device['username'] = ''
        device['password'] = ''
        device['default_enter'] = '\r'
        device['session_log'] = 'telnet_session.log'
    elif username and password:
        device['username'] = username
        device['password'] = password

    try:
        net_connect = ConnectHandler(**device)
        print("[DEBUG] Attempting connection with device config:")
        for k, v in device.items():
            if k in ("username", "password"):
                print(f"{k}: {'(hidden)' if v else '(none)'}")
            else:
                print(f"{k}: {v}")

        output = net_connect.send_config_set(config.splitlines())
        net_connect.disconnect()
        return jsonify({"message": "Success", "output": output})
    except (NetMikoTimeoutException, NetMikoAuthenticationException) as e:
        return jsonify({"message": f"Connection error: {str(e)}"}), 500
    except Exception as e:
        return jsonify({"message": f"Unexpected error: {str(e)}"}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')