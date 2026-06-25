import base64
import json
from io import BytesIO

import uvicorn
from fastapi import FastAPI, File, Form, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from PIL import Image
import google.generativeai as genai
import os

app = FastAPI(title="자율주행 버스 승객 안전 시스템 API v0.3")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Gemini API 설정
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "YOUR_API_KEY_HERE")
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-1.5-flash")

SYSTEM_PROMPT = """
당신은 자율주행 버스 내부 카메라를 모니터링하는 AI 안전 시스템입니다.
이미지를 분석하여 아래 JSON 형식으로만 응답하세요. 다른 텍스트는 절대 포함하지 마세요.

응답 형식:
{
  "situation_type": "EMERGENCY 또는 VULNERABLE 또는 NORMAL",
  "action": "STOP_IMMEDIATELY 또는 DEPLOY_SLOPE 또는 NONE",
  "description": "감지된 상황에 대한 한국어 설명 (1~2문장)",
  "detected_objects": ["감지된 객체 목록"],
  "confidence": 0.0~1.0 사이 신뢰도
}

판단 기준:
[EMERGENCY - 즉시 정차 + 119 신고]
- 승객이 좌석 밖 통로나 바닥에 쓰러져 있는 경우
- 신체가 좌석 경계를 명확히 벗어난 경우
- 의식불명이 의심되는 경우
- 주의: 좌석에 기대거나 고개를 숙이고 자는 경우는 NORMAL로 판단
- 주의: 판단이 불확실한 경우 반드시 NORMAL로 판단 (오탐 방지)

[VULNERABLE - 슬로프 자동 전개]
- 휠체어를 사용하는 승객이 탑승하는 경우
- 유모차를 동반한 승객이 탑승하는 경우
- 위 두 가지 경우에만 VULNERABLE로 판단

[NORMAL - 조치 없음]
- 승객이 좌석에 정상적으로 앉아 있는 경우
- 승객이 좌석에서 잠을 자거나 기대어 있는 경우
- 서있는 승객이 손잡이를 잡고 있는 경우
- 판단이 불확실한 모든 경우
""".strip()


def encode_image(image_bytes: bytes) -> Image.Image:
    """이미지 로드 및 최적화"""
    image = Image.open(BytesIO(image_bytes))
    max_size = (1024, 1024)
    image.thumbnail(max_size, Image.LANCZOS)
    return image


def generate_emergency_report(description: str, lat: float, lng: float, bus_id: str) -> str:
    """119 자동 신고 텍스트 생성"""
    return (
        f"[119 자동신고] {bus_id} 버스 내 응급환자 발생. "
        f"현재 위치: 위도 {lat}, 경도 {lng}. "
        f"{description} "
        f"즉시 출동 요청."
    )


def parse_response(content: str) -> dict:
    """Gemini 응답 JSON 파싱"""
    try:
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0]
        elif "```" in content:
            content = content.split("```")[1].split("```")[0]
        return json.loads(content.strip())
    except Exception:
        return {
            "situation_type": "NORMAL",
            "action": "NONE",
            "description": "상황 분석 중 오류가 발생했습니다.",
            "detected_objects": [],
            "confidence": 0.0
        }


@app.post("/analyze")
async def analyze(
    image: UploadFile = File(...),
    lat: float = Form(...),
    lng: float = Form(...),
    bus_id: str = Form(default="BUS-001")
):
    """
    승객 상태 분석 API

    - image: 차내 카메라 이미지 (유사환경 이미지)
    - lat: 현재 버스 위도 (응급상황 119 신고 시 사용)
    - lng: 현재 버스 경도 (응급상황 119 신고 시 사용)
    - bus_id: 버스 식별자
    """
    # 이미지 처리
    image_bytes = await image.read()
    pil_image = encode_image(image_bytes)

    # GPS 컨텍스트 (응급상황 신고용)
    gps_context = f"버스 ID: {bus_id} | 신고 위치: 위도 {lat}, 경도 {lng}"

    # Gemini API 멀티모달 추론
    prompt = f"{SYSTEM_PROMPT}\n\n{gps_context}\n\n위 이미지를 분석하여 승객 상태를 판단하세요."
    response = model.generate_content(
        [prompt, pil_image],
        generation_config=genai.types.GenerationConfig(
            temperature=0.1,
            max_output_tokens=512,
        )
    )

    # 응답 파싱
    result = parse_response(response.text)

    # 응급상황일 때만 119 신고 텍스트 생성 (GPS 활용)
    emergency_report = None
    if result.get("situation_type") == "EMERGENCY":
        emergency_report = generate_emergency_report(
            result.get("description", ""),
            lat, lng, bus_id
        )

    return {
        "bus_id": bus_id,
        "gps": {"lat": lat, "lng": lng},
        "situation_type": result.get("situation_type", "NORMAL"),
        "action": result.get("action", "NONE"),
        "description": result.get("description", ""),
        "detected_objects": result.get("detected_objects", []),
        "confidence": result.get("confidence", 0.0),
        "emergency_report": emergency_report
    }


@app.get("/health")
async def health():
    return {"status": "ok", "service": "자율주행 버스 승객 안전 시스템 v0.3"}


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=9000, reload=True)
