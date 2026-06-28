FROM python:3.12-alpine

LABEL maintainer="shellysim"
LABEL description="Shelly Plus Plug simulator for EET Solmate – MQTT to HTTP bridge"

WORKDIR /app

# paho-mqtt is the only runtime dependency
RUN pip install --no-cache-dir paho-mqtt==1.6.1

COPY app.py .

# Shelly API port (EET Solmate will connect here)
EXPOSE 80

HEALTHCHECK --interval=30s --timeout=5s --start-period=5s \
  CMD wget -qO- http://localhost/rpc/Shelly.GetStatus || exit 1

CMD ["python", "-u", "app.py"]
