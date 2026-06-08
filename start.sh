#!/bin/bash

# Start the background scanner process
echo "Starting background scanner..."
python main.py &

# Start the Streamlit dashboard on the port provided by Render
# Render automatically sets the PORT environment variable
export PORT="${PORT:-8501}"
echo "Starting Streamlit dashboard on port $PORT..."
streamlit run dashboard/app.py --server.port $PORT --server.address 0.0.0.0
