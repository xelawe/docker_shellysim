#!/usr/bin/env python3
"""
Shelly Plus Plug Simulator for EET Solmate
Replicates the behavior of xelawe/esp8266_shellysim as a Docker container.

- Subscribes to MQTT topic for power readings
- Serves a Shelly-compatible HTTP API on port 80
"""

import os
import time
import json
import logging
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse

import paho.mqtt.client as mqtt

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger("shellysim")

# ---------------------------------------------------------------------------
# Configuration via environment variables
# ---------------------------------------------------------------------------
MQTT_HOST     = os.environ.get("MQTT_HOST", "localhost")
MQTT_PORT     = int(os.environ.get("MQTT_PORT", "1883"))
MQTT_USER     = os.environ.get("MQTT_USER", "")
MQTT_PASS     = os.environ.get("MQTT_PASS", "")
MQTT_TOPIC_IN = os.environ.get("MQTT_TOPIC_IN", "shellysim/cmnd/apower")
MQTT_CLIENT   = os.environ.get("MQTT_CLIENT", "shellysim")
HTTP_PORT     = int(os.environ.get("HTTP_PORT", "80"))

# ---------------------------------------------------------------------------
# Shared state
# ---------------------------------------------------------------------------
state = {
    "apower": 40.0,   # Watts – updated by MQTT
}

# ---------------------------------------------------------------------------
# HTTP handler
# ---------------------------------------------------------------------------

SHELLY_RESPONSE_TEMPLATE = """\
{{"ble":{{}},"cloud":{{"connected":false}},\
"switch:0":{{"id":0,"source":"init","output":true,\
"apower":{apower:.1f},\
"voltage":234.3,"current":0.055,\
"aenergy":{{"total":1787.013,"by_minute":[25.160,75.913,75.480],"minute_ts":1758374839}},\
"temperature":{{"tC":39.7,"tF":103.5}}}}}}"""


class ShellyHandler(BaseHTTPRequestHandler):
    """Minimal HTTP server that mimics the Shelly Plus Plug API."""

    def log_message(self, fmt, *args):  # silence default access log spam
        log.debug("HTTP %s", fmt % args)

    def do_GET(self):
        parsed = urlparse(self.path)
        # The EET Solmate polls /rpc/Shelly.GetStatus (any path works per original)
        body = SHELLY_RESPONSE_TEMPLATE.format(apower=state["apower"])
        body_bytes = body.encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body_bytes)))
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        self.wfile.write(body_bytes)
        log.debug("GET %s → apower=%.1f W", self.path, state["apower"])


# ---------------------------------------------------------------------------
# MQTT callbacks
# ---------------------------------------------------------------------------

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        log.info("MQTT connected to %s:%d", MQTT_HOST, MQTT_PORT)
        client.publish(f"{MQTT_CLIENT}/tele/LWT", "online", retain=True)
        client.subscribe(MQTT_TOPIC_IN)
        log.info("Subscribed to %s", MQTT_TOPIC_IN)
    else:
        log.warning("MQTT connect failed, rc=%d – retrying…", rc)


def on_disconnect(client, userdata, rc):
    log.warning("MQTT disconnected (rc=%d)", rc)


def on_message(client, userdata, msg):
    try:
        value = float(msg.payload.decode().strip())
        state["apower"] = value
        log.info("MQTT ← %s = %.1f W", msg.topic, value)
    except ValueError:
        log.warning("Invalid payload on %s: %r", msg.topic, msg.payload)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def run_mqtt():
    client = mqtt.Client(client_id=MQTT_CLIENT)
    if MQTT_USER:
        client.username_pw_set(MQTT_USER, MQTT_PASS)
    client.will_set(f"{MQTT_CLIENT}/tele/LWT", "offline", retain=True)
    client.on_connect    = on_connect
    client.on_disconnect = on_disconnect
    client.on_message    = on_message

    while True:
        try:
            client.connect(MQTT_HOST, MQTT_PORT, keepalive=60)
            client.loop_forever()
        except Exception as exc:
            log.error("MQTT error: %s – reconnecting in 5 s", exc)
            time.sleep(5)


def run_http():
    server = HTTPServer(("0.0.0.0", HTTP_PORT), ShellyHandler)
    log.info("HTTP server listening on port %d", HTTP_PORT)
    server.serve_forever()


if __name__ == "__main__":
    log.info("Starting Shelly Simulator (MQTT→HTTP bridge)")
    log.info("  MQTT broker : %s:%d", MQTT_HOST, MQTT_PORT)
    log.info("  MQTT topic  : %s", MQTT_TOPIC_IN)
    log.info("  HTTP port   : %d", HTTP_PORT)

    t_mqtt = threading.Thread(target=run_mqtt, daemon=True, name="mqtt")
    t_mqtt.start()

    run_http()   # blocks main thread
