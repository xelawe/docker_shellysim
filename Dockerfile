FROM python:3.12-alpine

LABEL maintainer="shellysim"
LABEL description="Shelly Plus Plug simulator for EET Solmate – MQTT to HTTP bridge"

WORKDIR /app

# wget for healthcheck + paho-mqtt
RUN apk add --no-cache wget \
 && pip install --no-cache-dir paho-mqtt==1.6.1

COPY app.py .

# Shelly API port (EET Solmate will connect here)
EXPOSE 80

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s \
  CMD wget -qO- http://127.0.0.1:${HTTP_PORT:-80}/rpc/Shelly.GetStatus || exit 1

CMD ["python", "-u", "app.py"]
