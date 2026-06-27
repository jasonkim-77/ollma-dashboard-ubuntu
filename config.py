import os
import psutil

# pynvml (NVIDIA VRAM 실시간 모니터링 라이브러리) 안전 초기화 및 로드
try:
    import pynvml
    pynvml.nvmlInit()
    NVML_AVAILABLE = True
except Exception:
    NVML_AVAILABLE = False

# Ubuntu 시스템 표준 Ollama 로그 실제 타겟 저장 경로
LOG_PATH = "/var/log/ollama.log"

def get_system_ram():
    """서버의 전체 시스템 RAM 사용량과 총 공간 크기를 GB 단위로 반환합니다."""
    mem = psutil.virtual_memory()
    total_gb = mem.total / (1024 ** 3)
    used_gb = mem.used / (1024 ** 3)
    percent = mem.percent
    return used_gb, total_gb, percent

def get_gpu_vram():
    """서버의 첫 번째 NVIDIA GPU 카드의 실시간 VRAM 점유 현황을 추출합니다."""
    if not NVML_AVAILABLE:
        return 0.0, 0.0, 0.0
    try:
        handle = pynvml.nvmlDeviceGetHandleByIndex(0)
        info = pynvml.nvmlDeviceGetMemoryInfo(handle)
        total_gb = info.total / (1024 ** 3)
        used_gb = info.used / (1024 ** 3)
        percent = (info.used / info.total) * 100
        return used_gb, total_gb, percent
    except Exception:
        return 0.0, 0.0, 0.0

