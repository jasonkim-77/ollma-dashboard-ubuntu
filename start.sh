#!/usr/bin/env bash
set -e

pkill -f streamlit
nohup streamlit run log_analyzer.py --server.port 9999 --server.address 0.0.0.0 > ./dashboard.log 2>&1 &
