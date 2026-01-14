# PyEdgeTwin Dashboard
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
RUN pip install --no-cache-dir streamlit>=1.28 influxdb-client>=1.36 pandas>=2.0

# Copy dashboard application
COPY dashboard.py .

# Expose Streamlit port
EXPOSE 8501

# Streamlit configuration
ENV STREAMLIT_SERVER_PORT=8501
ENV STREAMLIT_SERVER_ADDRESS=0.0.0.0

CMD ["streamlit", "run", "dashboard.py"]
