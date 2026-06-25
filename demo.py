import requests
import streamlit as st
from PIL import Image

st.set_page_config(
    page_title="자율주행 버스 승객 안전 시스템",
    page_icon="🚌",
    layout="wide"
)

API_URL = "http://localhost:9000"

SITUATION_CONFIG = {
    "EMERGENCY": {
        "color": "#FF4444",
        "bg": "#FFE8E8",
        "icon": "🚨",
        "label": "응급상황",
        "action_label": "즉시 정차 + 119 자동 신고",
    },
    "VULNERABLE": {
        "color": "#FF8800",
        "bg": "#FFF3E0",
        "icon": "♿",
        "label": "교통약자 감지",
        "action_label": "슬로프 자동 전개",
    },
    "NORMAL": {
        "color": "#00AA44",
        "bg": "#E8F5E9",
        "icon": "✅",
        "label": "정상",
        "action_label": "없음",
    }
}

CRITERIA = {
    "EMERGENCY": [
        "좌석 밖 통로/바닥에 쓰러진 승객",
        "의식불명 의심 상황",
        "※ 좌석에서 자는 경우 → NORMAL",
        "※ 불확실한 경우 → NORMAL",
    ],
    "VULNERABLE": [
        "휠체어 사용 승객 탑승",
        "유모차 동반 승객 탑승",
    ],
    "NORMAL": [
        "정상 착석 승객",
        "수면/기댄 승객",
        "서서 손잡이 잡은 승객",
        "판단 불확실한 모든 경우",
    ]
}


def call_api(image_file, lat, lng, bus_id):
    files = {"image": (image_file.name, image_file.getvalue(), "image/jpeg")}
    data = {"lat": lat, "lng": lng, "bus_id": bus_id}
    response = requests.post(f"{API_URL}/analyze", files=files, data=data, timeout=30)
    return response.json()


def render_result(result: dict):
    situation = result.get("situation_type", "NORMAL")
    config = SITUATION_CONFIG.get(situation, SITUATION_CONFIG["NORMAL"])

    # 상황 배너
    st.markdown(f"""
    <div style="background:{config['bg']};border-left:6px solid {config['color']};
    padding:20px;border-radius:8px;margin:12px 0;">
        <h2 style="color:{config['color']};margin:0;">{config['icon']} {config['label']}</h2>
        <p style="margin:8px 0 0 0;font-size:16px;color:{config['color']};">
            <b>대응 조치: {config['action_label']}</b>
        </p>
    </div>
    """, unsafe_allow_html=True)

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("#### 📋 분석 결과")
        st.write(f"**상황 설명:** {result.get('description', '-')}")
        objects = result.get('detected_objects', [])
        st.write(f"**감지 객체:** {', '.join(objects) if objects else '없음'}")
        confidence = result.get('confidence', 0)
        st.progress(confidence)
        st.caption(f"신뢰도: {confidence * 100:.1f}%")
        if confidence < 0.6:
            st.warning("⚠️ 신뢰도가 낮습니다. 관제사 수동 확인을 권장합니다.")

    with col2:
        st.markdown("#### 📍 GPS 위치 정보")
        gps = result.get("gps", {})
        st.write(f"**버스 ID:** {result.get('bus_id', '-')}")
        st.write(f"**위도:** {gps.get('lat', '-')}")
        st.write(f"**경도:** {gps.get('lng', '-')}")
        if situation == "EMERGENCY":
            st.error("🚑 GPS 위치가 119 신고에 자동 포함됩니다.")
        else:
            st.info("ℹ️ GPS는 응급상황 발생 시에만 활용됩니다.")

    # 119 신고 텍스트
    if situation == "EMERGENCY" and result.get("emergency_report"):
        st.markdown("---")
        st.markdown("#### 🚑 119 자동 신고 내용")
        st.error(result["emergency_report"])
        with st.expander("📋 신고 내용 복사"):
            st.code(result["emergency_report"])

    with st.expander("🔧 원본 응답 JSON"):
        st.json(result)


# ── UI 레이아웃 ──

st.title("🚌 자율주행 버스 승객 안전 및 교통약자 지원 시스템")
st.caption("Gemini API 기반 멀티모달 분석 | 실제 배포 시 vLLM + LLaVA로 교체 예정")

st.info("""
📌 **테스트 이미지 안내** (유사 환경 이미지 활용 / Unsplash·Pexels CC0)
- 🚨 응급상황: 실내 쓰러진 사람 이미지 5장
- ♿ 교통약자: 휠체어/유모차 이미지 6장
- ✅ 정상상황: 실내 착석 승객 이미지 3장
""")

st.divider()

# 사이드바
with st.sidebar:
    st.header("🛰 버스 정보")
    st.caption("GPS는 응급상황 시 119 신고에만 활용됩니다.")
    bus_id = st.text_input("버스 ID", value="BUS-042")
    lat = st.number_input("위도 (Latitude)", value=37.5665, format="%.4f")
    lng = st.number_input("경도 (Longitude)", value=126.9780, format="%.4f")

    st.divider()
    st.markdown("**빠른 GPS 설정**")
    if st.button("서울 시청"):
        lat, lng = 37.5662, 126.9784
    if st.button("강남역"):
        lat, lng = 37.4979, 127.0276
    if st.button("홍대입구"):
        lat, lng = 37.5572, 126.9244

    st.divider()
    try:
        res = requests.get(f"{API_URL}/health", timeout=3)
        st.success("✅ API 서버 연결됨") if res.status_code == 200 else st.error("❌ API 서버 오류")
    except Exception:
        st.warning("⚠️ API 서버 미연결\nbackend/main.py를 먼저 실행해주세요.")

# 메인
col_upload, col_result = st.columns([1, 1])

with col_upload:
    st.subheader("📷 이미지 업로드")
    uploaded_file = st.file_uploader(
        "테스트 이미지를 업로드하세요",
        type=["jpg", "jpeg", "png"],
        help="응급상황 / 교통약자 / 정상 시나리오 이미지"
    )

    if uploaded_file:
        image = Image.open(uploaded_file)
        st.image(image, caption=f"업로드: {uploaded_file.name}", use_column_width=True)

        expected = st.selectbox(
            "예상 판단 결과 (검증용)",
            ["선택 안 함", "EMERGENCY", "VULNERABLE", "NORMAL"]
        )

        st.divider()
        analyze_btn = st.button("🔍 승객 상태 분석", type="primary", use_container_width=True)
    else:
        st.info("👆 이미지를 업로드하면 분석을 시작할 수 있습니다.")
        analyze_btn = False
        expected = "선택 안 함"

with col_result:
    st.subheader("📊 분석 결과")

    if uploaded_file and analyze_btn:
        with st.spinner("Gemini API가 이미지를 분석 중입니다..."):
            try:
                uploaded_file.seek(0)
                result = call_api(uploaded_file, lat, lng, bus_id)
                render_result(result)

                if expected != "선택 안 함":
                    actual = result.get("situation_type", "NORMAL")
                    if expected == actual:
                        st.success(f"✅ 판단 정확 — 예상: {expected} / 실제: {actual}")
                    else:
                        st.error(f"❌ 판단 불일치 — 예상: {expected} / 실제: {actual}")

            except requests.exceptions.ConnectionError:
                st.error("❌ API 서버에 연결할 수 없습니다.\n backend/main.py를 먼저 실행해주세요.")
            except Exception as e:
                st.error(f"❌ 오류 발생: {str(e)}")
    else:
        st.markdown("""
        <div style="background:#F8F9FA;border-radius:8px;padding:40px;
        text-align:center;color:#999;height:300px;
        display:flex;align-items:center;justify-content:center;">
            <div>
                <div style="font-size:48px;">🔍</div>
                <div style="margin-top:12px;">이미지 업로드 후<br>분석 버튼을 클릭하세요</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

# 판단 기준
st.divider()
st.subheader("📌 판단 기준")
col1, col2, col3 = st.columns(3)

for col, (key, color, bg, title, action) in zip(
    [col1, col2, col3],
    [
        ("EMERGENCY", "#FF4444", "#FFE8E8", "🚨 EMERGENCY", "즉시 정차 + 119 자동 신고"),
        ("VULNERABLE", "#FF8800", "#FFF3E0", "♿ VULNERABLE", "슬로프 자동 전개"),
        ("NORMAL", "#00AA44", "#E8F5E9", "✅ NORMAL", "조치 없음"),
    ]
):
    criteria_html = "".join([f"<li style='font-size:13px;'>{c}</li>" for c in CRITERIA[key]])
    with col:
        st.markdown(f"""
        <div style="background:{bg};padding:16px;border-radius:8px;
        border-left:4px solid {color};min-height:160px;">
            <b style="color:{color};">{title}</b><br>
            <small style="color:#666;">→ {action}</small>
            <ul style="margin-top:8px;padding-left:16px;">{criteria_html}</ul>
        </div>
        """, unsafe_allow_html=True)
