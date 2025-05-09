from flask import Flask, request, jsonify
from netmiko import ConnectHandler, NetMikoTimeoutException, NetMikoAuthenticationException

app = Flask(__name__)

@app.route('/api/send-config', methods=['POST'])
def send_config():
    data = request.get_json()

    ip = data.get('ip')
    device_type = data.get('deviceType')
    protocol = data.get('protocol')
    username = data.get('username', '')
    password = data.get('password', '')
    config = data.get('config')

    if protocol == 'telnet':
        device_type = 'cisco_ios_telnet'

    device = {
        'device_type': device_type,
        'host': ip,
        'username': username,
        'password': password,
    }

    if protocol == 'telnet' and not username:
        device['username'] = ''
        device['password'] = ''
        device['default_enter'] = '\r'

    try:
        net_connect = ConnectHandler(**device)
        output = net_connect.send_config_set(config.splitlines())
        net_connect.disconnect()
        return jsonify({"message": "Success", "output": output})
    except (NetMikoTimeoutException, NetMikoAuthenticationException) as e:
        return jsonify({"message": f"Connection error: {str(e)}"}), 500
    except Exception as e:
        return jsonify({"message": f"Unexpected error: {str(e)}"}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
