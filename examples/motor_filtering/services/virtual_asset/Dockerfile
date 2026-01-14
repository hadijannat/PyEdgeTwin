# Virtual Motor Asset Simulator
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
RUN pip install --no-cache-dir "paho-mqtt>=2.0.0,<3.0.0"

# Copy simulator script
COPY simulator.py .

CMD ["python", "simulator.py"]
