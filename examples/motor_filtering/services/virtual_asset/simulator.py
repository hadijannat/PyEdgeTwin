#!/usr/bin/env python3
"""Virtual Motor Asset Simulator for PyEdgeTwin Demo.

Simulates a motor temperature sensor with:
- Sinusoidal daily temperature variation
- Gaussian measurement noise
- Occasional anomalous spikes (simulating faults)
- Configurable via environment variables

Output: MQTT messages to sensors/motor-001/temperature
"""

from __future__ import annotations

import json
import math
import os
import random
import signal
import sys
import time
from datetime import datetime, timezone

import paho.mqtt.client as mqtt
from paho.mqtt.enums import CallbackAPIVersion

# Configuration from environment
MQTT_HOST = os.environ.get("MQTT_HOST", "localhost")
MQTT_PORT = int(os.environ.get("MQTT_PORT", "1883"))
ASSET_ID = os.environ.get("ASSET_ID", "motor-001")
PUBLISH_INTERVAL = float(os.environ.get("PUBLISH_INTERVAL", "1.0"))
SEED = os.environ.get("SEED")

# Simulation parameters
BASE_TEMPERATURE = 45.0  # Base motor temperature in Celsius
DAILY_VARIATION = 5.0    # Temperature varies +/- 5C over a "day" (60 seconds)
NOISE_STDDEV = 0.5       # Gaussian noise standard deviation
ANOMALY_PROBABILITY = 0.02  # 2% chance of anomaly per reading
ANOMALY_MAGNITUDE_MIN = 5.0
ANOMALY_MAGNITUDE_MAX = 15.0


class MotorSimulator:
    """Simulates a motor with temperature sensor."""

    def __init__(self, seed: int | None = None) -> None:
        if seed is not None:
            random.seed(seed)
        self.time_offset = 0.0

    def get_temperature(self) -> tuple[float, bool]:
        """
        Generate a simulated temperature reading.

        Returns:
            Tuple of (temperature, is_anomaly)
        """
        # Base temperature with sinusoidal variation
        # Simulate a "day" as 60 seconds for demo purposes
        daily_phase = (self.time_offset / 60.0) * 2 * math.pi
        temp = BASE_TEMPERATURE + DAILY_VARIATION * math.sin(daily_phase)

        # Add Gaussian noise
        temp += random.gauss(0, NOISE_STDDEV)

        # Occasional anomaly (fault simulation)
        is_anomaly = random.random() < ANOMALY_PROBABILITY
        if is_anomaly:
            spike = random.uniform(ANOMALY_MAGNITUDE_MIN, ANOMALY_MAGNITUDE_MAX)
            spike *= random.choice([-1, 1])  # Positive or negative
            temp += spike

        self.time_offset += PUBLISH_INTERVAL
        return round(temp, 2), is_anomaly


def main() -> None:
    """Main entry point."""
    print(f"Starting Virtual Motor Asset Simulator")
    print(f"  MQTT Broker: {MQTT_HOST}:{MQTT_PORT}")
    print(f"  Asset ID: {ASSET_ID}")
    print(f"  Publish Interval: {PUBLISH_INTERVAL}s")
    print(f"  Seed: {SEED or 'random'}")

    # Initialize simulator
    seed = int(SEED) if SEED else None
    simulator = MotorSimulator(seed=seed)

    # Set up MQTT client with Paho v2 API
    client = mqtt.Client(
        callback_api_version=CallbackAPIVersion.VERSION2,
        client_id=f"virtual-asset-{ASSET_ID}",
    )

    connected = False

    def on_connect(client, userdata, flags, reason_code, properties):
        nonlocal connected
        if reason_code.is_failure:
            print(f"Connection failed: {reason_code}")
        else:
            print(f"Connected to MQTT broker: {reason_code.getName()}")
            connected = True

    def on_disconnect(client, userdata, flags, reason_code, properties):
        nonlocal connected
        connected = False
        print(f"Disconnected: {reason_code.getName()}")

    client.on_connect = on_connect
    client.on_disconnect = on_disconnect

    # Connect to broker
    print(f"Connecting to MQTT broker...")
    try:
        client.connect(MQTT_HOST, MQTT_PORT)
        client.loop_start()
    except Exception as e:
        print(f"Failed to connect: {e}")
        sys.exit(1)

    # Wait for connection
    for _ in range(10):
        if connected:
            break
        time.sleep(1)

    if not connected:
        print("Failed to connect to MQTT broker")
        sys.exit(1)

    # Signal handling for graceful shutdown
    running = True

    def signal_handler(signum, frame):
        nonlocal running
        print(f"\nReceived signal {signum}, shutting down...")
        running = False

    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)

    # Main publishing loop
    topic = f"sensors/{ASSET_ID}/temperature"
    message_count = 0

    try:
        while running:
            # Generate reading
            temperature, is_anomaly = simulator.get_temperature()

            # Create payload
            payload = {
                "asset_id": ASSET_ID,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "value": temperature,
                "unit": "celsius",
                "sensor_type": "temperature",
                "simulated_anomaly": is_anomaly,  # For debugging only
            }

            # Publish
            result = client.publish(topic, json.dumps(payload), qos=1)
            message_count += 1

            # Log
            anomaly_marker = " [ANOMALY]" if is_anomaly else ""
            print(f"[{message_count}] {topic}: {temperature}°C{anomaly_marker}")

            # Wait for next reading
            time.sleep(PUBLISH_INTERVAL)

    except KeyboardInterrupt:
        print("\nKeyboard interrupt")

    finally:
        print(f"Published {message_count} messages")
        client.loop_stop()
        client.disconnect()


if __name__ == "__main__":
    main()
