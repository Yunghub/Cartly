import asyncio
import json
import os
import socket
import ssl
import tempfile
from typing import Callable, Optional

import paho.mqtt.client as mqtt

MQTT_HOST = "mqtt.yungcz.com"
MQTT_PORT = 8883
MQTT_USERNAME = "cartly"
MQTT_PASSWORD = "cartly"
MQTT_TOPIC_TELEMETRY = "smarttrolley/trolley_01/telemetry"
MQTT_TOPIC_CONFIG = "smarttrolley/trolley_01/config"

# ISRG Root X1 — the Let's Encrypt root CA used by the broker
_ISRG_ROOT_X1 = """\
-----BEGIN CERTIFICATE-----
MIIFazCCA1OgAwIBAgIRAIIQz7DSQONZRGPgu2OCiwAwDQYJKoZIhvcNAQELBQAw
TzELMAkGA1UEBhMCVVMxKTAnBgNVBAoTIEludGVybmV0IFNlY3VyaXR5IFJlc2Vh
cmNoIEdyb3VwMRUwEwYDVQQDEwxJU1JHIFJvb3QgWDEwHhcNMTUwNjA0MTEwNDM4
WhcNMzUwNjA0MTEwNDM4WjBPMQswCQYDVQQGEwJVUzEpMCcGA1UEChMgSW50ZXJu
ZXQgU2VjdXJpdHkgUmVzZWFyY2ggR3JvdXAxFTATBgNVBAMTDElTUkcgUm9vdCBY
MTCCAiIwDQYJKoZIhvcNAQEBBQADggIPADCCAgoCggIBAK3oJHP0FDfzm54rVygc
h77ct984kIxuPOZXoHj3dcKi/vVqbvYATyjb3miGbESTtrFj/RQSa78f0uoxmyF+
0TM8ukj13Xnfs7j/EvEhmkvBioZxaUpmZmyPfjxwv60pIgbz5MDmgK7iS4+3mX6U
A5/TR5d8mUgjU+g4rk8Kb4Mu0UlXjIB0ttov0DiNewNwIRt18jA8+o+u3dpjq+sW
T8KOEUt+zwvo/7V3LvSye0rgTBIlDHCNAymg4VMk7BPZ7hm/ELNKjD+Jo2FR3qyH
B5T0Y3HsLuJvW5iB4YlcNHlsdu87kGJ55tukmi8mxdAQ4Q7e2RCOFvu396j3x+UC
B5iPNgiV5+I3lg02dZ77DnKxHZu8A/lJBdiB3QW0KtZB6awBdpUKD9jf1b0SHzUv
KBds0pjBqAlkd25HN7rOrFleaJ1/ctaJxQZBKT5ZPt0m9STJEadao0xAH0ahmbWn
OlFuhjuefXKnEgV4We0+UXgVCwOPjdAvBbI+e0ocS3MFEvzG6uBQE3xDk3SzynTn
jh8BCNAw1FtxNrQHusEwMFxIt4I7mKZ9YIqioymCzLq9gwQbooMDQaHWBfEbwrbw
qHyGO0aoSCqI3Haadr8faqU9GY/rOPNk3sgrDQoo//fb4hVC1CLQJ13hef4Y53CI
rU7m2Ys6xt0nUW7/vGT1M0NPAgMBAAGjQjBAMA4GA1UdDwEB/wQEAwIBBjAPBgNV
HRMBAf8EBTADAQH/MB0GA1UdDgQWBBR5tFnme7bl5AFzgAiIyBpY9umbbjANBgkq
hkiG9w0BAQsFAAOCAgEAVR9YqbyyqFDQDLHYGmkgJykIrGF1XIpu+ILlaS/V9lZL
ubhzEFnTIZd+50xx+7LSYK05qAvqFyFWhfFQDlnrzuBZ6brJFe+GnY+EgPbk6ZGQ
3BebYhtF8GaV0nxvwuo77x/Py9auJ/GpsMiu/X1+mvoiBOv/2X/qkSsisRcOj/KK
NFtY2PwByVS5uCbMiogziUwthDyC3+6WVwW6LLv3xLfHTjuCvjHIInNzktHCgKQ5
ORAzI4JMPJ+GslWYHb4phowim57iaztXOoJwTdwJx4nLCgdNbOhdjsnvzqvHu7Ur
TkXWStAmzOVyyghqpZXjFaH3pO3JLF+l+/+sKAIuvtd7u+Nxe5AW0wdeRlN8NwdC
jNPElpzVmbUq4JUagEiuTDkHzsxHpFKVK7q4+63SM1N95R1NbdWhscdCb+ZAJzVc
oyi3B43njTOQ5yOf+1CceWxG1bQVs5ZufpsMljq4Ui0/1lvh+wjChP4kqKOJ2qxq
4RgqsahDYVvTH9w7jXbyLeiNdd8XM2w9U/t7y0Ff/9yi0GE44Za4rF2LN9d11TPA
mRGunUHBcnWEvgJBQl9nJEiU0Zsnvgc/ubhPgXRR4Xq37Z0j4r7g1SgEEzwxA57d
emyPxgcYxn/eR44/KJ4EBs+lVDR3veyJm+kXQ99b21/+jh5Xos1AnX5iItreGCc=
-----END CERTIFICATE-----
"""

_client: Optional[mqtt.Client] = None
_loop: Optional[asyncio.AbstractEventLoop] = None
_on_telemetry: Optional[Callable] = None
_ca_path: Optional[str] = None
_UDP_PORT = 4210
_ENABLE_DIRECT_STREAM = os.getenv("ENABLE_DIRECT_STREAM", "0") == "1"
_DIRECT_STREAM_HOST = os.getenv("DIRECT_STREAM_HOST", "").strip()


def _get_local_ip() -> str:
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return ""


def _on_connect(client, userdata, flags, rc):
    if rc == 0:
        client.subscribe(MQTT_TOPIC_TELEMETRY)
        print(f"[MQTT] Connected — subscribed to {MQTT_TOPIC_TELEMETRY}")
        ip = _DIRECT_STREAM_HOST or _get_local_ip()
        if _ENABLE_DIRECT_STREAM and ip:
            msg = json.dumps({"directHost": ip, "directEnabled": True})
            client.publish(MQTT_TOPIC_CONFIG, msg, qos=1)
            print(f"[MQTT] Advertised direct stream → {ip}:{_UDP_PORT}")
    else:
        print(f"[MQTT] Connect failed rc={rc}")


def _on_disconnect(client, userdata, rc):
    print(f"[MQTT] Disconnected rc={rc}")


def _on_message(client, userdata, msg):
    try:
        data = json.loads(msg.payload.decode())
    except Exception as e:
        print(f"[MQTT] Bad payload: {e}")
        return
    if _loop and _on_telemetry:
        asyncio.run_coroutine_threadsafe(_on_telemetry(data), _loop)


def start_mqtt(on_telemetry: Callable, loop: asyncio.AbstractEventLoop) -> None:
    global _client, _loop, _on_telemetry, _ca_path
    _loop = loop
    _on_telemetry = on_telemetry

    # Write the CA cert to a temp file so paho can load it
    tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".pem", delete=False)
    tmp.write(_ISRG_ROOT_X1)
    tmp.close()
    _ca_path = tmp.name

    _client = mqtt.Client(client_id="trolley_dashboard", clean_session=True)
    _client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)
    _client.tls_set(ca_certs=_ca_path, cert_reqs=ssl.CERT_REQUIRED)
    _client.on_connect = _on_connect
    _client.on_disconnect = _on_disconnect
    _client.on_message = _on_message

    try:
        _client.connect_async(MQTT_HOST, MQTT_PORT, keepalive=60)
        _client.loop_start()
        print(f"[MQTT] Connecting to {MQTT_HOST}:{MQTT_PORT} …")
    except Exception as e:
        print(f"[MQTT] Start error: {e}")


def stop_mqtt() -> None:
    global _client, _ca_path
    if _client:
        _client.loop_stop()
        _client.disconnect()
        _client = None
    if _ca_path and os.path.exists(_ca_path):
        os.unlink(_ca_path)
        _ca_path = None


def publish_config(payload: dict) -> None:
    if _client and _client.is_connected():
        msg = json.dumps(payload)
        _client.publish(MQTT_TOPIC_CONFIG, msg, qos=1)
        print(f"[MQTT] Config → {msg}")
    else:
        print("[MQTT] Cannot publish: not connected")
