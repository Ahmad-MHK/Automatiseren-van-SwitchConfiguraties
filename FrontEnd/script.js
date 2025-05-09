let devices = []

document.getElementById('devicesFile').addEventListener('change', async function () {
  const file = this.files[0]
  const output = document.getElementById('output')
  if (!file) return

  try {
    const text = await file.text()
    devices = JSON.parse(text)
    const select = document.getElementById('deviceSelect')
    select.innerHTML = ''

    if (!Array.isArray(devices) || devices.length === 0) {
      output.style.color = 'red'
      output.textContent = '❌ Invalid or empty devices.json'
      return
    }

    devices.forEach((device, index) => {
      const option = document.createElement('option')
      option.value = index
      option.textContent = `${device.name || 'Unnamed'} (${device.ip || 'no IP'})`
      select.appendChild(option)
    })

    select.selectedIndex = 0
    output.style.color = 'green'
    output.textContent = '✅ Devices loaded. Select one and send.'
  } catch (err) {
    output.style.color = 'red'
    output.textContent = '❌ Error parsing devices.json: ' + err.message
  }
})

async function sendConfig() {
  const output = document.getElementById('output')
  output.style.color = 'black'
  output.textContent = '⏳ Sending config...'

  const fileInput = document.getElementById('configFile')
  if (fileInput.files.length === 0) {
    output.style.color = 'red'
    output.textContent = '❌ Please upload a config (.txt) file.'
    return
  }

  const configFile = fileInput.files[0]
  const configText = await configFile.text()

  const selectElement = document.getElementById('deviceSelect')
  if (!selectElement || selectElement.selectedIndex < 0) {
    output.style.color = 'red'
    output.textContent = '❌ Device selection not found or invalid.'
    return
  }

  const selectedDevice = devices[selectElement.value]
  const protocol = document.getElementById('protocolSelect').value

  const data = {
    ip: selectedDevice.ip,
    deviceType: selectedDevice.device_type,
    protocol: protocol,
    config: configText
  }

  if ('username' in selectedDevice && 'password' in selectedDevice) {
    data.username = selectedDevice.username
    data.password = selectedDevice.password
  }

  try {
    const res = await fetch('http://localhost:5000/api/send-config', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    })

    const result = await res.json()
    if (res.ok) {
      output.style.color = 'green'
      output.textContent = '✅ SUCCESS:\n' + (result.output || result.message)
    } else {
      output.style.color = 'red'
      output.textContent = '❌ ERROR: ' + (result.message || 'Unknown error')
    }
  } catch (e) {
    output.style.color = 'red'
    output.textContent = '❌ Network error: Failed to fetch\nMake sure your backend is running at http://localhost:5000'
  }
}