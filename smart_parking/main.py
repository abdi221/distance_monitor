from machine import Pin, PWM
import utime
import uasyncio as asyncio
import network
import socket
import json

trigger = Pin(2, Pin.OUT)
echo = Pin(3, Pin.IN)
buzzer = PWM(Pin(15))
buzzer.duty_u16(0)
led = Pin(18, Pin.OUT)

MAX_WAIT_US = 30000
MAX_PULSE_US = 30000
SAFE_DIST = 50.0
WARN_DIST = 20.0
BEEP_FREQ = 1200
BEEP_DUTY = 32767

_last_blink = 0
blink_state = False

WIFI_SSID = "iotlab"
WIFI_PASS = "modermodemet3"

#Global that holds latest reading for web UI
latest_dist = None # float in cm or None if no reading yet
latest_ts = 0 # milliseconds timestamp of last reading


def ultra_sen():
    trigger.low()
    utime.sleep_us(2)
    trigger.high()
    utime.sleep_us(10)
    trigger.low()

    start_wait = utime.ticks_us()
    while echo.value() == 0:
        if utime.ticks_diff(utime.ticks_us(), start_wait) > MAX_WAIT_US:
            return None

    signal_off = utime.ticks_us()

    while echo.value() == 1:
        if utime.ticks_diff(utime.ticks_us(), signal_off) > MAX_PULSE_US:
            return None

    signalon = utime.ticks_us()
    time_passed = utime.ticks_diff(signalon, signal_off)
    distance = (time_passed * 0.0343) / 2
    return distance

# Sensor sampling task
async def sensor_task():
    global latest_dist, latest_ts, _last_blink, blink_state
    buzzer.freq(BEEP_FREQ)
    while True:
        dist = ultra_sen()
        latest_dist = dist
        latest_ts = utime.ticks_ms()

        if dist is None:
            now = utime.ticks_ms()
            if utime.ticks_diff(now, _last_blink) > 250:
                blink_state = not blink_state
                led.value(1 if blink_state else 0)
                _last_blink = now
            # short beep once per second
            buzzer.duty_u16(BEEP_DUTY)
            await asyncio.sleep_ms(25)
            buzzer.duty_u16(0)
            await asyncio.sleep_ms(100)
        else:
            # simple distance-dependent timing
            delay = max(20, int(dist * 5))
            if dist > SAFE_DIST:
                led.low()
                buzzer.duty_u16(0)
                await asyncio.sleep_ms(delay)
            elif WARN_DIST < dist <= SAFE_DIST:
                now = utime.ticks_ms()
                if utime.ticks_diff(now, _last_blink) > delay:
                    blink_state = not blink_state
                    led.value(1 if blink_state else 0)
                    _last_blink = now
                buzzer.duty_u16(BEEP_DUTY)
                await asyncio.sleep_ms(30)
                buzzer.duty_u16(0)
                await asyncio.sleep_ms(delay)
            else:
                led.value(1)
                buzzer.duty_u16(BEEP_DUTY)
                await asyncio.sleep_ms(int(delay/2))
                buzzer.duty_u16(0)
                await asyncio.sleep_ms(int(delay/4))

# Simple async webserver that serves root page and /distance JSON ---
ROOT_HTML = """\
<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <title>Pico W Distance Monitor</title>
  <style>
    body { font-family: Arial, sans-serif; text-align:center; margin-top:40px; }
    .meter { font-size: 48px; font-weight:700; margin: 20px; }
    .small { font-size: 16px; color: #666; }
    .bar { width: 80%; height: 24px; background:#eee; margin: 20px auto; border-radius:12px; overflow:hidden; }
    .fill { height:100%; background: #ff5c33; width:0%; transition: width 0.2s; }
  </style>
</head>
<body>
  <h1>Pico W Distance Monitor</h1>
  <div class="meter" id="dist">-- cm</div>
  <div class="small">Last update: <span id="ts">--</span></div>
  <div class="bar"><div id="fill" class="fill"></div></div>
  <div class="small">(refreshes ~3x/sec)</div>

<script>
async function fetchDist(){
  try {
    const res = await fetch('/distance');
    const j = await res.json();
    const el = document.getElementById('dist');
    const ts = document.getElementById('ts');
    const fill = document.getElementById('fill');

    if (j.distance === null){
      el.textContent = "no reading";
      ts.textContent = new Date(j.ts).toLocaleTimeString();
      fill.style.width = "0%";
    } else {
      let d = j.distance.toFixed(1);
      el.textContent = d + " cm";
      ts.textContent = new Date(j.ts).toLocaleTimeString();
      // map distance to fill (0 cm => 100%, SAFE_DIST => 0%)
      const SAFE = """ + str(SAFE_DIST) + """;
      let pct = Math.max(0, Math.min(100, Math.round((1 - (j.distance / SAFE)) * 100)));
      fill.style.width = pct + "%";
    }
  } catch (e) {
    console.log('fetch error', e);
  }
}

setInterval(fetchDist, 300);
window.onload = fetchDist;
</script>
</body>
</html>
"""

async def serve_client(reader, writer):
    try:
        request_line = await reader.readline()
        if not request_line:
            await writer.aclose()
            return
        # parse the first line e.g. b"GET / HTTP/1.1\r\n"
        req = request_line.decode().split()
        if len(req) < 2:
            await writer.aclose()
            return
        method = req[0]
        path = req[1]

        # drain headers
        while True:
            h = await reader.readline()
            if not h or h == b'\r\n':
                break

        if path == '/' or path == '/index.html':
            body = ROOT_HTML
            header = 'HTTP/1.0 200 OK\r\nContent-Type: text/html\r\nContent-Length: {}\r\n\r\n'.format(len(body))
            await writer.awrite(header)
            await writer.awrite(body)
        elif path == '/distance':
            # produce JSON with latest reading
            # read global latest_dist/latest_ts
            global latest_dist, latest_ts
            payload = {
                'distance': None if latest_dist is None else float(latest_dist),
                'ts': int(latest_ts)
            }
            body = json.dumps(payload)
            header = 'HTTP/1.0 200 OK\r\nContent-Type: application/json\r\nContent-Length: {}\r\n\r\n'.format(len(body))
            await writer.awrite(header)
            await writer.awrite(body)
        else:
            body = 'Not found'
            header = 'HTTP/1.0 404 NOT FOUND\r\nContent-Length: {}\r\n\r\n'.format(len(body))
            await writer.awrite(header)
            await writer.awrite(body)

    except Exception as e:
        # minimal error handling, so it don't crash server
        try:
            await writer.awrite('HTTP/1.0 500\r\n\r\n')
        except:
            pass
    finally:
        try:
            await writer.aclose()
        except:
            pass

# WiFi connect
def connect_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    if not wlan.isconnected():
        print('Connecting to WiFi...')
        wlan.connect(WIFI_SSID, WIFI_PASS)
        # wait for connection
        for _ in range(30): 
            if wlan.isconnected():
                break
            utime.sleep(1)
    if wlan.isconnected():
        ip = wlan.ifconfig()[0]
        print('Connected, IP =', ip)
        return ip
    else:
        print('WiFi connect failed')
        return None

# main entrypoint 
async def main():
    ip = connect_wifi()
    if ip is None:
        print("No network; webserver won't start.")
    else:
        # start the async server on port 80
        print("Starting web server on port 80...")
        asyncio.create_task(asyncio.start_server(serve_client, "0.0.0.0", 80))

    # start sensor sampling loop
    asyncio.create_task(sensor_task())

    # keep alive 
    while True:
        await asyncio.sleep(60)

# run the event loop
try:
    asyncio.run(main())
finally:
    asyncio.new_event_loop()

