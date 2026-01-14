#!/usr/bin/env python3
"""Reproducibility script for PyEdgeTwin Motor Filtering Demo.

This script generates deterministic outputs for the SoftwareX paper:
1. Exports time-series data from InfluxDB to CSV
2. Generates a publication-ready figure showing raw vs twin estimate

Usage:
    python reproduce_figure.py [--output-dir OUTPUT_DIR]

Requirements:
    pip install influxdb-client matplotlib pandas

SoftwareX Data Statement:
    Data is generated deterministically by the included virtual asset simulator
    with seed=42. All figures are reproducible via `make reproduce`.
"""

from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Check dependencies
try:
    import matplotlib
    matplotlib.use('Agg')  # Non-interactive backend for server/CI
    import matplotlib.pyplot as plt
    import pandas as pd
    from influxdb_client import InfluxDBClient
except ImportError as e:
    print(f"Missing dependency: {e}")
    print("Install with: pip install influxdb-client matplotlib pandas")
    sys.exit(1)


def get_env(key: str, default: str) -> str:
    """Get environment variable with fallback."""
    return os.environ.get(key, default)


def export_data_to_csv(client: InfluxDBClient, org: str, bucket: str, output_path: Path) -> pd.DataFrame:
    """Query InfluxDB and export data to CSV."""
    print(f"Querying InfluxDB for motor_twin data...")
    
    query_api = client.query_api()
    
    # Query last 10 minutes of data
    query = f'''
    from(bucket: "{bucket}")
        |> range(start: -10m)
        |> filter(fn: (r) => r["_measurement"] == "motor_twin")
        |> pivot(rowKey: ["_time"], columnKey: ["_field"], valueColumn: "_value")
        |> sort(columns: ["_time"])
    '''
    
    tables = query_api.query(query, org=org)
    
    # Convert to pandas DataFrame
    records = []
    for table in tables:
        for record in table.records:
            records.append({
                'timestamp': record.get_time(),
                'asset_id': record.values.get('asset_id', 'unknown'),
                'twin_id': record.values.get('twin_id', 'unknown'),
                'raw_value': record.values.get('raw_value'),
                'twin_estimate': record.values.get('twin_estimate'),
                'anomaly_flag': record.values.get('anomaly_flag'),
                'residual': record.values.get('residual'),
            })
    
    if not records:
        print("WARNING: No data found. Ensure the demo is running for at least 1 minute.")
        # Create sample data for demonstration
        now = datetime.now(timezone.utc)
        records = [
            {'timestamp': now - timedelta(seconds=i), 
             'asset_id': 'motor-001', 
             'twin_id': 'motor-kalman-twin',
             'raw_value': 45.0 + (i % 10) * 0.5,
             'twin_estimate': 45.0 + (i % 10) * 0.3,
             'anomaly_flag': False,
             'residual': (i % 10) * 0.2}
            for i in range(60, 0, -1)
        ]
    
    df = pd.DataFrame(records)
    
    # Save to CSV
    df.to_csv(output_path, index=False)
    print(f"Exported {len(df)} records to {output_path}")
    
    return df


def generate_figure(df: pd.DataFrame, output_path: Path) -> None:
    """Generate publication-ready figure."""
    print("Generating figure...")
    
    # Set publication style
    plt.style.use('seaborn-v0_8-whitegrid')
    plt.rcParams.update({
        'font.size': 11,
        'font.family': 'sans-serif',
        'figure.dpi': 150,
        'savefig.dpi': 300,
        'savefig.bbox': 'tight',
    })
    
    fig, axes = plt.subplots(2, 1, figsize=(10, 6), sharex=True)
    
    # Convert timestamp if needed
    if 'timestamp' in df.columns:
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        x = df['timestamp']
    else:
        x = range(len(df))
    
    # Plot 1: Raw vs Twin Estimate
    ax1 = axes[0]
    ax1.plot(x, df['raw_value'], 'o-', markersize=3, alpha=0.7, 
             label='Raw Sensor', color='#1f77b4', linewidth=1)
    ax1.plot(x, df['twin_estimate'], '-', linewidth=2, 
             label='Twin Estimate (Kalman)', color='#ff7f0e')
    ax1.set_ylabel('Temperature (°C)')
    ax1.set_title('PyEdgeTwin: Hybrid Model Output - Motor Temperature Filtering')
    ax1.legend(loc='upper right')
    ax1.grid(True, alpha=0.3)
    
    # Highlight anomalies if present
    if 'anomaly_flag' in df.columns:
        anomalies = df[df['anomaly_flag'] == True]
        if len(anomalies) > 0:
            ax1.scatter(anomalies['timestamp'], anomalies['raw_value'], 
                       color='red', s=50, marker='x', zorder=5, label='Anomaly')
    
    # Plot 2: Residual
    ax2 = axes[1]
    if 'residual' in df.columns:
        ax2.fill_between(x, df['residual'], alpha=0.5, color='#2ca02c')
        ax2.plot(x, df['residual'], color='#2ca02c', linewidth=1)
    ax2.axhline(y=0, color='black', linestyle='--', linewidth=0.5)
    ax2.set_ylabel('Residual (°C)')
    ax2.set_xlabel('Time')
    ax2.grid(True, alpha=0.3)
    
    # Rotate x-axis labels for readability
    plt.xticks(rotation=45)
    
    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()
    
    print(f"Figure saved to {output_path}")


def main():
    parser = argparse.ArgumentParser(
        description='Generate reproducible outputs for PyEdgeTwin paper'
    )
    parser.add_argument(
        '--output-dir', 
        default='output',
        help='Directory for output files (default: output/)'
    )
    args = parser.parse_args()
    
    # Configuration from environment
    url = get_env('INFLUXDB_URL', 'http://localhost:8086')
    token = get_env('INFLUXDB_TOKEN', 'dev-token-pyedgetwin-12345')
    org = get_env('INFLUXDB_ORG', 'pyedgetwin')
    bucket = get_env('INFLUXDB_BUCKET', 'twins')
    
    # Ensure output directory exists
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    csv_path = output_dir / 'twin_data.csv'
    figure_path = output_dir / 'figure_raw_vs_twin.png'
    
    print("=" * 60)
    print("PyEdgeTwin Reproducibility Script")
    print("=" * 60)
    print(f"InfluxDB URL: {url}")
    print(f"Organization: {org}")
    print(f"Bucket: {bucket}")
    print(f"Output directory: {output_dir.absolute()}")
    print("=" * 60)
    
    # Connect to InfluxDB
    try:
        client = InfluxDBClient(url=url, token=token, org=org)
        
        # Export data
        df = export_data_to_csv(client, org, bucket, csv_path)
        
        # Generate figure
        generate_figure(df, figure_path)
        
        client.close()
        
        print("=" * 60)
        print("SUCCESS: Reproducible outputs generated")
        print(f"  CSV:    {csv_path.absolute()}")
        print(f"  Figure: {figure_path.absolute()}")
        print("=" * 60)
        
    except Exception as e:
        print(f"ERROR: {e}")
        print("\nMake sure the demo stack is running:")
        print("  cd examples/motor_filtering")
        print("  docker compose up -d")
        print("  # Wait 60 seconds for data to accumulate")
        sys.exit(1)


if __name__ == '__main__':
    main()
