# **Distance Sensor System – Raspberry Pi Pico W**

This project uses a Raspberry Pi Pico W together with an ultrasonic sensor to measure distance, trigger alerts, and publish live readings over Wi-Fi. The goal was to build something small, reliable, and resilient enough to keep running even when the hardware or software misbehaves.

---

## **What the Project Does**

* Measures distance using an HC-SR04 ultrasonic sensor
* Displays the reading on a simple web dashboard
* Flashes an LED and activates a buzzer if something gets too close
* Recovers automatically from hangs or wiring faults
* Never blocks or freezes—thanks to built-in fault-handling

You can leave the device running and expect it to stay alive without babysitting.

---

## **Hardware Used**

* Raspberry Pi Pico W
* HC-SR04 ultrasonic sensor
* 1× LED + resistor
* Buzzer (PWM capable)
* Jumper wires
* 100 nF capacitor (recommended, helps stabilize the sensor)

The hardware setup is straightforward: trigger and echo pins go to any two GPIOs, the LED and buzzer sit on their own pins, and that’s it.

---

## **Key Features**

### **1. Reliable Distance Measurement**

The sensor code includes:

* A timeout so the Pico doesn’t hang waiting for the echo signal
* A “sanity check” to filter out impossible values
* Graceful handling of loose wires or sensor failures

If the sensor stops responding, the program keeps running and reports the issue instead of getting stuck.

### **2. Automatic Recovery With Watchdog Timer**

A hardware watchdog resets the Pico if the code ever stops responding.
This protects against:

* Infinite loops
* Accidental blocking code
* Unexpected software crashes

The reset is fast, so the system comes back online without user intervention.

### **3. Web Dashboard**

The Pico W hosts a tiny web server. Opening the IP address in a browser shows:

* Live distance values
* Alert status
* Optional logs or sensor errors

Works on phone or laptop as long as they’re on the same network.

### **4. Responsive Alerts**

The buzzer and LED behave based on distance:

* Safe range → quiet
* Object too close → LED ON and buzzer pulses faster the closer it gets

The timing adapts dynamically.

---

## **How to Run It**

1. Flash MicroPython onto the Pico W (if not already done).
2. Copy `main.py` onto the device using Thonny or your preferred tool.
3. Update the Wi-Fi name and password at the top of the file.
4. Reset the Pico.
5. Open the IP address shown in the console in your browser.

If everything is wired correctly, you’ll see live readings immediately.

---

## **Troubleshooting**

* **Sensor not responding**
  Check trigger/echo wiring and confirm the sensor has stable power. The dashboard will still load even if the sensor fails.

* **Frequent resets**
  Usually means the watchdog isn’t being fed—look for any blocking code added recently.

* **Inaccurate readings**
  Place a small capacitor (100 nF) across VCC and GND on the sensor. This often fixes jitter.

---

## **Why This Project Matters**

The project started as a simple distance sensor, but the focus shifted to reliability—something many small embedded systems lack. Handling real-world faults (loose cables, bad readings, unexpected software states) turned out to be more important than measuring distance itself.

The result is a small, Wi-Fi-enabled device that behaves predictably even when things go wrong.

---

## **Future Ideas**

* Add MQTT support for integration with Home Assistant
* Store logs locally or send them to a server
* Add a small OLED screen
* Use multiple sensors for room mapping

---

