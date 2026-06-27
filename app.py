import streamlit as st
import pandas as pd
import os
import time
import plotly.express as px
from datetime import datetime

import log_parser

# 화면 좌우 가득 채우는 와이드 뷰 레이아웃 고정
st.set_page_config(page_title="Ollama Ubuntu 로그 분석기", layout="wide")

st.markdown("""
    <style>
        /* 🆕 오리지널 stHeader/stAppToolbar 라인과 완전 통합 */
        div.st-key-fixed_header {
            position: fixed;
            top: 0;
            left: 0;
            width: calc(100vw - 200px) !important;
            height: 3.75rem; /* Streamlit 순정 헤더/툴바 정격 높이 (60px) */
            background-color: transparent; /* 배색을 투명하게 하여 순정 헤더 바 위에 얹음 */
            z-index: 999999; /* 최상위 레이어 고정 */
            display: flex;
            align-items: center;
            padding-left: 2rem !important;
        }

        /* 🎛️ 툴바 라인 삽입을 위해 본문 시작 패딩을 딱 60px 헤더만큼만 하강 */
        .block-container {
            padding-top: 4.5rem !important; /* 헤더 높이 직후 바로 본문이 붙도록 최적화 */
            padding-bottom: 1.5rem !important;
            padding-left: 2rem !important;
            padding-right: 2rem !important;
            max-width: 100% !important;
        }
        
        /* 툴바용 타이틀 폰트 다운사이징 */
        .toolbar-title {
            font-size: 1.25rem !important;
            font-weight: 800;
            color: #cyanAccent;
            margin: 0;
            line-height: 3.75rem;
        }
        
        [data-testid="stMetricSimple"] {
            background-color: #f8f9fa; padding: 15px; border-radius: 10px; border: 1px solid #e9ecef;
        }
        .advice-box {
            background-color: #333; padding: 20px; border-radius: 8px;
            border-left: 5px solid #2196f3; font-size: 1.1rem; margin-bottom: 20px;
        }

        .st-emotion-cache-5d70d { margin: 10px 0 0; }
    </style>
""", unsafe_allow_html=True)

LOG_PATH = "/var/log/ollama.log"

# =========================================================================
# 📌 [구조 개정] 순정 툴바(stAppToolbar) 좌측 공역에 완벽 결합 시퀀스
# =========================================================================
with st.container(key="fixed_header"):
    # 60px 높이 안에서 터지지 않도록 가로로 3분할 슬롯 전개
    ctrl_col1, ctrl_col2, ctrl_col3 = st.columns([2.5, 3.5, 4])
    
    with ctrl_col1:
        st.markdown(f"<div style='line-height: 3.75rem; color: gray; font-size: 0.85rem;'>⏱️ 갱신: <code>{datetime.now().strftime('%H:%M:%S')}</code></div>", unsafe_allow_html=True)
        
    with ctrl_col2:
        # 타이틀 옆 공간에 갱신 시간을 한 줄로 슬림하게 배치
        st.markdown(f"<div style='line-height: 3.75rem; color: gray; font-size: 0.85rem;'>⏱️ Updated: <code>{datetime.now().strftime('%H:%M:%S')}</code></div>", unsafe_allow_html=True)
        
    with ctrl_col3:
        refresh_options = {"🔄 수동": 0, "🔄 1분": 60, "🔄 5분": 300, "🔄 10분": 600}
        # ⚠️ label_visibility="collapsed"를 주입하여 셀렉트박스의 제목 라인을 지워버려야 툴바에 한 줄로 쏙 들어갑니다!
        selected_label = st.selectbox(
            "", 
            list(refresh_options.keys()), 
            index=1, 
            label_visibility="collapsed"
        )
        refresh_interval = refresh_options[selected_label]


# ==========================================
# 📊 1. 시스템 상태 대시보드 (CPU / RAM / VRAM)
# ==========================================
with st.expander("🖥️ 1. 시스템 상태 대시보드", expanded=True):
    sys_metrics = log_parser.get_system_metrics()

    sys_col1, sys_col2, sys_col3 = st.columns(3)
    with sys_col1:
        st.markdown(f"**중앙 처리 장치 (CPU)**")
        st.progress(int(sys_metrics["cpu_pct"]))
        st.caption(f"⚡ **점유율:** {sys_metrics['cpu_pct']:.1f}%")

    with sys_col2:
        st.markdown(f"**시스템 메모리 (RAM)**")
        st.progress(int(sys_metrics["ram_pct"]))
        st.caption(f"💾 **사용량:** {sys_metrics['ram_used']:.2f} GB / {sys_metrics['ram_total']:.2f} GB ({sys_metrics['ram_pct']:.1f}%)")

    with sys_col3:
        st.markdown(f"**비디오 메모리 (VRAM)**")
        if sys_metrics["vram_total"] > 0:
            st.progress(int(sys_metrics["vram_pct"]))
            st.caption(f"🎨 **사용량:** {sys_metrics['vram_used']:.2f} GB / {sys_metrics['vram_total']:.2f} GB ({sys_metrics['vram_pct']:.1f}%)")
        else:
            st.progress(0)
            st.caption("⚠️ NVIDIA GPU 드라이버를 로드할 수 없거나 CPU 모드입니다.")

#st.markdown("---")

# 백엔드 파서 데이터 호출
if not os.path.exists(LOG_PATH):
    st.error(f"❌ '{LOG_PATH}' 자리에 로그 파일이 존재하지 않습니다.")
else:
    df, error_count, current_model_name, current_ctx_size = log_parser.parse_ollama_gin_logs(LOG_PATH)
        
    # ==========================================
    # 💡 [신규 추가 요청 반영] 모델 컨텍스트 임계 한계 예측 및 마진 가이드 대시보드
    # ==========================================
    with st.expander("🔮 2. VRAM 마진 기반 컨텍스트 확장 한계 예측", expanded=True):
    
        # 여유 VRAM 및 안전 마진 1GB 공제값 연산
        free_vram = sys_metrics["vram_total"] - sys_metrics["vram_used"]
        vram_for_extension = free_vram - 1.0  # 1GB 마진 공제
        
        # 보수적인 KV 캐시 소비율 대입연산 (1k 토큰당 대략 0.45GB 소모 가정)
        kv_cache_factor_per_1k = 0.45 
        
        if sys_metrics["vram_total"] > 0:
            max_additional_tokens_k = max(0.0, vram_for_extension / kv_cache_factor_per_1k)
            recommended_max_ctx = current_ctx_size + int(max_additional_tokens_k * 1000)
            
            advice_col1, advice_col2, advice_col3 = st.columns(3)
            with advice_col1:
                st.info(f"🏷️ **현재 상주 모델**: `{current_model_name}`")
            with advice_col2:
                st.warning(f"📏 **현재 설정된 컨텍스트**: `{current_ctx_size:,} tokens`")
            with advice_col3:
                st.success(f"💎 **1GB 마진 제외 순수 가용 VRAM**: `{max(0.0, vram_for_extension):.2f} GB` (여유: {free_vram:.2f} GB)")
                
            # 조정을 위한 액션 가이드 메시지 상자 렌더링
            if vram_for_extension > 0.1:
                st.markdown(f"""
                <div class="advice-box">
                    💡 <b>컨텍스트 사이즈 조정 가이드:</b><br>
                    현재 시스템에 안전 마진 1GB를 확보하고도 <b>{vram_for_extension:.2f} GB</b>의 여유 비디오 메모리가 더 있습니다.<br>
                    Ollama Modelfile 매개변수에서 <code>num_ctx</code> 사이즈를 최대 <b>{recommended_max_ctx:,} tokens</b>까지 추가로 확장 업(Size Up)해도 하드웨어가 버틸 수 있습니다.
                </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown(f"""
                <div class="advice-box" style="background-color: darkgray; border-left: 5px solid #f44336;">
                    ⚠️ <b>컨텍스트 메모리 포화 주의:</b><br>
                    현재 비디오 메모리 마진이 1GB 미만(<b>{free_vram:.2f} GB 여유</b>)으로 매우 타이트합니다.<br>
                    더 큰 컨텍스트로 조정하면 OOM(비디오 메모리 폭발 에러)이나 CPU 오프로딩으로 인한 심각한 속도 저하가 발생할 수 있습니다. 현재 상태 유지를 권장합니다.
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("CPU 추론 환경이므로 GPU VRAM 확장 예측 스펙을 건너뜁니다.")

    #st.markdown("---")

    # ==========================================
    # 📊 3. 올라마 통계 대시보드
    # ==========================================
    with st.expander("📊 3. 올라마 통계 대시보드", expanded=True):
    
        is_error_row = df["Status"].astype(str).str.contains("TRUNCATED|ERROR|CRITICAL", na=False, case=False)
        df_normal = df[~is_error_row]
        
        total_requests = len(df_normal)
        total_tokens = pd.to_numeric(df_normal["Tokens"], errors='coerce').sum()
        avg_tokens = total_tokens / total_requests if total_requests > 0 else 0.0
        
        stat_col1, stat_col2, stat_col3, stat_col4 = st.columns(4)
        stat_col1.metric("총 API 요청 수", f"{total_requests:,} 건")
        stat_col2.metric("총 생성된 토큰 수", f"{int(total_tokens):,} tokens")
        stat_col3.metric("📈 회당 평균 생성 토큰 수", f"{avg_tokens:.1f} tokens")
        stat_col4.metric("🚨 최근 감지된 총 오류 수", f"{error_count:,} 건")
        
        with st.expander("📊 Graphs", expanded=False):
            chart_col1, chart_col2 = st.columns(2)
            with chart_col1:
                st.subheader("🤖 모델별 누적 사용량 분배")
                if not df_normal.empty:
                    model_counts = df_normal["Model"].value_counts().reset_index()
                    model_counts.columns = ["Model", "Count"]
                    st.plotly_chart(px.pie(model_counts, values="Count", names="Model", hole=0.4), use_container_width=True)
                else: st.info("시각화할 모델 통계 기록이 없습니다.")
                    
            with chart_col2:
                st.subheader("⏱️ API 엔드포인트별 응답 시간 (ms)")
                if not df_normal.empty:
                    st.plotly_chart(px.box(df_normal, x="Path", y="Duration(ms)", color="Method"), use_container_width=True)
                else: st.info("시각화할 트래픽 응답 속도가 없습니다.")

    #st.markdown("---")

    # ==========================================
    # 📋 4. 통합 로그 타임라인 (붉은색 바탕 조건부 배색 가동)
    # ==========================================
    with st.expander("📋 4. 통합 처리 내역 및 오류 로그 타임라인", expanded=True):
        st.write("일반 API 요청 처리 및 토큰 속도 내역 사이에 발생한 트렁케이트 문맥 초과 오류가 시간대별 흐름에 맞춰 병합된 표입니다.")
        
        if not df.empty:
            df_timeline = df.sort_values("Timestamp", ascending=False).head(50)
            
            def highlight_errors(row):
                status_str = str(row['Status'])
                if any(keyword in status_str.upper() for keyword in ["TRUNCATED", "ERROR", "CRITICAL"]):
                    return ['background-color: #F004; color: #ffffff; font-weight: bold;'] * len(row)
                return [''] * len(row)
            
    #        df_styled = df_timeline.style.apply(highlight_errors, axis=1)
            # 스타일러 엔진 가동 및 소수점 자리수 출력 포맷 강제 고정 (.format)
            df_styled = (
                df_timeline.style
                .apply(highlight_errors, axis=1)
                .format({
                    "Duration(ms)": "{:.1f}",  # 소수점 첫째자리 (ex: 2000.0)
                    "GenTime(s)": "{:.2f}",    # 소수점 둘째자리 (ex: 146.67)
                    "TPS(토큰/초)": "{:.1f}"    # 소수점 첫째자리 (ex: 17.5)
                })
            )
            st.dataframe(df_styled, use_container_width=True, height=500)
        else:
            st.warning("💡 타임라인에 로드할 수 있는 레코드가 없습니다.")

# 타이머 작동
if refresh_interval > 0:
    time.sleep(refresh_interval)
    st.rerun()

