# 🔌 shellysim

> **Shelly Plus Plug Simulator für den EET Solmate** – als Docker Container statt ESP8266

[![Docker](https://img.shields.io/badge/Docker-ready-2496ED?logo=docker&logoColor=white)](https://hub.docker.com)
[![Python](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)](https://python.org)
[![MQTT](https://img.shields.io/badge/MQTT-paho-660066?logo=eclipse-mosquitto&logoColor=white)](https://eclipse.dev/paho/)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)

Der [EET Solmate](https://www.eet.energy/) kann über einen echten [Shelly Plus Plug](https://www.shelly.com/de/products/shop/shelly-plus-plug-s) den Hausverbrauch messen. Wer bereits andere Energiemessgeräte im Einsatz hat, kann stattdessen einen Shelly **simulieren**.

Dieses Projekt ist eine Docker-Portierung von [xelawe/esp8266_shellysim](https://github.com/xelawe/esp8266_shellysim) – die gleiche Logik, ohne ESP8266-Hardware, direkt auf dem Heimserver oder NAS.

---

## Wie es funktioniert

```
Energiemessgerät / Home Assistant / Node-RED
          │
          │  MQTT publish  (Hausverbrauch in Watt)
          ▼
  shellysim/cmnd/apower
          │
  ┌───────┴────────────────────────┐
  │      shellysim Container       │
  │  • MQTT subscriber             │
  │  • HTTP server (Port 80)       │
  └───────┬────────────────────────┘
          │
          │  HTTP GET /rpc/Shelly.GetStatus
          ▼
      EET Solmate 2
```

Der Container:
1. Abonniert ein MQTT-Topic und speichert den letzten Leistungswert (Watt).
2. Stellt diesen Wert über eine Shelly-kompatible HTTP-API auf **Port 80** bereit.
3. Der EET Solmate fragt diesen Endpunkt regelmäßig ab und nutzt `switch:0.apower` als Hausverbrauch.

---

## Schnellstart

### Voraussetzungen

- Docker & Docker Compose (oder Portainer)
- Laufender MQTT-Broker im Netzwerk

### 1. Repository klonen

```bash
git clone https://github.com/xelawe/shellysim.git
cd shellysim
```

### 2. `docker-compose.yml` anpassen

```yaml
environment:
  MQTT_HOST: "192.168.1.10"        # ← IP deines MQTT-Brokers
  MQTT_PORT: "1883"
  MQTT_USER: ""                    # leer lassen wenn keine Authentifizierung
  MQTT_PASS: ""
  MQTT_TOPIC_IN: "shellysim/cmnd/apower"
```

### 3. Container starten

```bash
docker compose up -d
```

### 4. HTTP-Endpunkt testen

```bash
curl http://localhost/rpc/Shelly.GetStatus
```

Erwartete Antwort:
```json
{
  "ble": {},
  "cloud": {"connected": false},
  "switch:0": {
    "id": 0,
    "source": "init",
    "output": true,
    "apower": 40.0,
    "voltage": 234.3,
    "current": 0.055
  }
}
```

### 5. Testwert per MQTT senden

```bash
mosquitto_pub -h 192.168.1.10 -t shellysim/cmnd/apower -m 350
```

Ein erneuter `curl`-Aufruf zeigt jetzt `"apower": 350.0`.

---

## Deployment via Portainer Stack

Falls du Portainer verwendest, gibt es zwei Wege:

### Option A – Image lokal bauen (empfohlen)

Dateien auf den Host kopieren, Image einmalig bauen:

```bash
docker build -t shellysim:latest .
```

Dann in Portainer unter **Stacks → Add Stack → Web editor** dieses Compose einfügen:

```yaml
services:
  shellysim:
    image: shellysim:latest
    container_name: shellysim
    restart: unless-stopped
    ports:
      - "80:80"
    environment:
      MQTT_HOST: "192.168.1.10"
      MQTT_PORT: "1883"
      MQTT_USER: ""
      MQTT_PASS: ""
      MQTT_TOPIC_IN: "shellysim/cmnd/apower"
      HTTP_PORT: "80"
      MQTT_CLIENT: "shellysim"
```

### Option B – Git Repository

In Portainer unter **Stacks → Add Stack → Repository** die URL dieses Repos und den Pfad zum `docker-compose.yml` angeben. Portainer klont und baut automatisch.

---

## Konfigurationsreferenz

| Variable        | Standard                     | Beschreibung                                  |
|-----------------|------------------------------|-----------------------------------------------|
| `MQTT_HOST`     | `localhost`                  | Hostname oder IP des MQTT-Brokers             |
| `MQTT_PORT`     | `1883`                       | Port des MQTT-Brokers                         |
| `MQTT_USER`     | *(leer)*                     | MQTT-Benutzername (optional)                  |
| `MQTT_PASS`     | *(leer)*                     | MQTT-Passwort (optional)                      |
| `MQTT_TOPIC_IN` | `shellysim/cmnd/apower`      | Topic mit dem Hausverbrauch in Watt           |
| `MQTT_CLIENT`   | `shellysim`                  | MQTT Client-ID und Topic-Präfix               |
| `HTTP_PORT`     | `80`                         | Port der Shelly HTTP-API im Container         |

> **Port 80 bereits belegt?** Linke Seite im Port-Mapping ändern: `"8080:80"` – und im EET Solmate denselben Port eintragen.

---

## EET Solmate konfigurieren

Im Solmate-Webinterface einen **Shelly Plus Plug** als Messgerät hinzufügen:

| Feld | Wert |
|------|------|
| IP-Adresse | IP des Docker-Hosts |
| Port | `80` (oder der gemappte Port) |

Der Solmate pollt `/rpc/Shelly.GetStatus` und liest `switch:0.apower` als aktuellen Hausverbrauch.

---

## MQTT-Topics

| Topic                    | Payload      | Richtung | Beschreibung                               |
|--------------------------|--------------|----------|--------------------------------------------|
| `shellysim/cmnd/apower`  | `<float>`    | ← Input  | Hausverbrauch in Watt                      |
| `shellysim/tele/LWT`     | `online`     | → Output | Retained, beim Verbindungsaufbau           |
| `shellysim/tele/LWT`     | `offline`    | → Output | Retained, Last Will bei Verbindungsabbruch |

---

## Credits

Basiert auf [xelawe/esp8266_shellysim](https://github.com/xelawe/esp8266_shellysim) von xelawe.
