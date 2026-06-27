# log_parser.py

import re
import os
import pandas as pd
import streamlit as st
import psutil
from datetime import datetime

try:
    import pynvml
    pynvml.nvmlInit()
    NVML_AVAILABLE = True
except Exception:
    NVML_AVAILABLE = False

COLUMNS_SPEC = ["Timestamp", "Status", "Duration(ms)", "IP", "Method", "Path", "Model", "Tokens", "GenTime(s)", "TPS(토큰/초)"]

def get_system_metrics():
    """CPU, RAM, VRAM의 실시간 사용량과 총 용량을 계측합니다."""
    cpu_pct = psutil.cpu_percent(interval=None)
    mem = psutil.virtual_memory()
    ram_used = mem.used / (1024 ** 3)
    ram_total = mem.total / (1024 ** 3)
    ram_pct = mem.percent
    
    vram_used, vram_total, vram_pct = 0.0, 0.0, 0.0
    if NVML_AVAILABLE:
        try:
            handle = pynvml.nvmlDeviceGetHandleByIndex(0)
            info = pynvml.nvmlDeviceGetMemoryInfo(handle)
            vram_used = info.used / (1024 ** 3)
            vram_total = info.total / (1024 ** 3)
            vram_pct = (info.used / info.total) * 100
        except:
            pass
            
    return {
        "cpu_pct": cpu_pct,
        "ram_used": ram_used, "ram_total": ram_total, "ram_pct": ram_pct,
        "vram_used": vram_used, "vram_total": vram_total, "vram_pct": vram_pct
    }

def parse_duration_to_seconds(dur_str):
    try:
        dur_str = dur_str.strip().lower()
        match = re.match(r"([0-9\.]+)\s*([a-zµ]+)?", dur_str)
        if not match: return 0.0
        value = float(match.group(1))
        unit = match.group(2)
        if unit == "ms": return value / 1000.0
        elif unit in ["µs", "us"]: return value / 1000000.0
        elif unit == "ns": return value / 1000000000.0
        return value
    except:
        return 0.0

def parse_ollama_gin_logs(file_path):
    """정상 처리 내역과 컨텍스트 설정 및 트렁케이트 오류를 단일 타임라인으로 통합합니다."""
    combined_records = []
    total_error_count = 0
    detected_context_size = 2048 
    
    gin_pattern = re.compile(
        r"(?:(?P<sys_date>\d{4}-\d{2}-\d{2})[T\s](?P<sys_time>\d{2}:\d{2}:\d{2})[^\s]*\s+)??"
        r"\[GIN\]\s+(?P<date>\d{4}/\d{2}/\d{2})?\s*-?\s*(?P<time>\d{2}:\d{2}:\d{2})?\s*\|\s*"
        r"(?P<status>\d{3})\s*\|\s*"
        r"(?P<duration>[^\s\|]+)\s*\|\s*"
        r"(?P<ip>[0-9\.]+)\s*\|\s*"
        r"(?P<method>POST|GET)\s+"
        r"\"(?P<path>[^\"]+)\""
    )
    
    recent_model = "알 수 없음"
    recent_tokens = 0
    recent_total_time_sec = 0.0
    recent_direct_tps = -1.0
    last_valid_datetime = datetime.now()
    
    if not os.path.exists(file_path):
        return pd.DataFrame(columns=COLUMNS_SPEC), 0, recent_model, detected_context_size
        
    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()
    except Exception:
        return pd.DataFrame(columns=COLUMNS_SPEC), 0, recent_model, detected_context_size

    # 🔗 [정격 복구] 완벽한 시간 순 추적을 위해 단일 대포 루프로 통합 가동합니다.
    for idx, line in enumerate(lines):
        line_str = line.strip()
        line_lower = line_str.lower()
        
        # 표준 시각 추적
        time_match = re.search(r"(\d{4}-\d{2}-\d{2}).(\d{2}:\d{2}:\d{2})", line_str)
        if time_match:
            try:
                last_valid_datetime = datetime.strptime(f"{time_match.group(1)} {time_match.group(2)}", "%Y-%m-%d %H:%M:%S")
            except: pass

        # 컨텍스트 사이즈 할당 로그 추적
        ctx_match = re.search(r"n_ctx\s*=\s*(\d+)", line_lower)
        if not ctx_match:
            ctx_match = re.search(r"ctx_size\s*=\s*(\d+)", line_lower)
        if ctx_match:
            detected_context_size = int(ctx_match.group(1))

        if "model" in line_lower:
            model_match = re.search(r'"model"\s*:\s*"([^"]+)"', line_str, re.IGNORECASE)
            if not model_match: model_match = re.search(r'model=([^\s,]+)', line_str)
            if model_match: recent_model = model_match.group(1).strip('"').split("/")[-1]

        # 🎯 [핵심 필터 회로]: 시스템 설정 오염 로그를 차단하고, 순수 print_timing 구역에서만 값을 포획합니다.
        if "print_timing" in line_lower:
            ts_match = re.search(r"([0-9\.]+)\s*t/s", line_str, re.IGNORECASE)
            if ts_match: 
                recent_direct_tps = float(ts_match.group(1))
            
            # 🔬 오직 추론 출력 완료 시점인 'eval time' 스냅샷에서만 정격 토큰 양을 카운트합니다.
            if "eval time" in line_lower and "prompt" not in line_lower:
                token_match = re.search(r"(\d+)\s*tokens", line_str, re.IGNORECASE)
                if token_match: 
                    recent_tokens = int(token_match.group(1))
            
            if "total time" in line_lower:
                time_match_dur = re.search(r"total time\s*=\s*([^\s,\|]+)", line_str, re.IGNORECASE)
                if time_match_dur: 
                    recent_total_time_sec = parse_duration_to_seconds(time_match_dur.group(1))

        # 에러 로그 검출
        is_error = False
        error_label = "⚠️ 일반 오류"
        if "truncated = 0" in line_lower or "truncated=0" in line_lower:
            pass
        else:
            if "level=error" in line_lower or "exception" in line_lower:
                is_error = True
                error_label = "💥 SYSTEM ERROR"
            elif "truncated =" in line_lower or "truncated=" in line_lower:
                trunc_val_match = re.search(r"truncated\s*=\s*([1-9]\d*)", line_lower)
                if trunc_val_match:
                    is_error = True
                    task_match = re.search(r"task\s*(\d+)", line_lower)
                    task_id = f" (Task {task_match.group(1)})" if task_match else ""
                    error_label = f"✂️ CONTEXT TRUNCATED{task_id}"

            if is_error and "[GIN]" not in line_str:
                total_error_count += 1
                combined_records.append({
                    "Timestamp": last_valid_datetime, "Status": error_label, "Duration(ms)": 0.0,
                    "IP": "SYSTEM", "Method": "CRITICAL", "Path": line_str[:40] + "...", "Model": recent_model,
                    "Tokens": 0, "GenTime(s)": 0.0, "TPS(토큰/초)": 0.0
                })

        # GIN 로그 포착 시 즉시 위에서 누적된 최근 메트릭 변수 결속 후 발행
        match = gin_pattern.search(line_str)
        if match:
            d = match.groupdict()
            api_path = d['path']
            
            # 노이즈 트래픽 청소 시 상태값 드레인(Drain) 리셋
            if any(keyword in api_path for keyword in ["/api/blob", "/api/tags", "/api/version", "/api/show"]):
                recent_tokens, recent_total_time_sec, recent_direct_tps = 0, 0.0, -1.0
                continue
            
            display_path = api_path[:15] + "..." if len(api_path) > 15 else api_path
            duration_ms = parse_duration_to_seconds(d['duration']) * 1000.0
            
            if d.get('sys_date') and d.get('sys_time'): dt_str = f"{d['sys_date']} {d['sys_time']}"
            elif d.get('date') and d.get('time'): dt_str = f"{d['date']} {d['time']}"
            else: dt_str = last_valid_datetime.strftime("%Y-%m-%d %H:%M:%S")
            
            try: timestamp = datetime.strptime(dt_str, "%Y-%m-%d %H:%M:%S")
            except: timestamp = last_valid_datetime

            tps = round(recent_direct_tps, 2) if recent_direct_tps >= 0.0 else (round(recent_tokens / recent_total_time_sec, 2) if recent_tokens > 0 and recent_total_time_sec > 0 else 0.0)

            combined_records.append({
                "Timestamp": timestamp, "Status": d['status'], "Duration(ms)": duration_ms,
                "IP": d['ip'], "Method": d['method'], "Path": display_path, "Model": recent_model,
                "Tokens": recent_tokens, "GenTime(s)": round(recent_total_time_sec, 3) if recent_total_time_sec > 0 else 0.0,
                "TPS(토큰/초)": tps
            })
            # 동기화 완료 후 장부 소거
            recent_tokens, recent_total_time_sec, recent_direct_tps = 0, 0.0, -1.0

    df_result = pd.DataFrame(combined_records) if combined_records else pd.DataFrame(columns=COLUMNS_SPEC)
    
    if "TPS(토큰/초)" in df_result.columns:
        df_result["TPS(토큰/초)"] = pd.to_numeric(df_result["TPS(토큰/초)"], errors='coerce').round(1).fillna(0.0)
        
    if "GenTime(s)" in df_result.columns:
        df_result["GenTime(s)"] = pd.to_numeric(df_result["GenTime(s)"], errors='coerce').round(2).fillna(0.0)

    return df_result, total_error_count, recent_model, detected_context_size
