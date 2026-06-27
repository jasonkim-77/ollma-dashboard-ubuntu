#!/usr/bin/env bash
set -e

PORT=9999

echo "[1/5] system packages..."
sudo apt update
sudo apt install -y python3 python3-pip python3-venv net-tools

echo "[2/5] create venv..."
python3 -m venv .venv

echo "[3/5] upgrade pip..."
./.venv/bin/pip install --upgrade pip

echo "[4/5] install python packages..."
./.venv/bin/pip install \
    streamlit \
    plotly \
    pandas \
    requests \
    ollama \
    watchdog \
    psutil \
    pynvml

echo "[5/5] firewall setup..."
sudo ufw allow $PORT || true
sudo ufw enable || true

echo "[DONE] run: ./start.sh"
