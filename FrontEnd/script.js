async function sendConfig() {
  const output = document.getElementById('output');
  output.textContent = 'Sending...';

  const fileInput = document.getElementById('configFile');
  let configText = document.getElementById('config').value;

  if (fileInput.files.length > 0) {
    const file = fileInput.files[0];
    configText = await file.text();
  }

  const data = {
    ip: document.getElementById('ip').value,
    deviceType: document.getElementById('deviceType').value,
    protocol: document.getElementById('protocol').value,
    username: document.getElementById('username').value,
    password: document.getElementById('password').value,
    config: configText
  };

  try {
    const res = await fetch('http://localhost:5000/api/send-config', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    });

    const result = await res.json();
    if (res.ok) {
      output.textContent = '✅ SUCCESS:\n' + (result.output || result.message);
    } else {
      output.textContent = '❌ ERROR: ' + (result.message || 'Unknown error');
    }
  } catch (e) {
    output.textContent = '❌ Network error: ' + e.message;
  }
}