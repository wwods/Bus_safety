# Autonomous Bus Passenger Safety System

멀티모달 LLM으로 자율주행 버스 내 카메라 이미지를 분석해 응급상황·교통약자를 자동 감지하고 대응 신호를 출력하는 시스템.

## Overview

```
Camera Image + GPS
      |
FastAPI Backend
      |
Groq API (LLaMA 4 Scout 17B)
      |
EMERGENCY      VULNERABLE     NORMAL
즉시 정차       슬로프 전개     조치 없음
GPS + 119 신고
```

실제 배포 시 vLLM + LLaVA-1.6으로 교체 가능한 구조로 설계.

## Classification Criteria

| 클래스 | 조건 | 대응 |
|---|---|---|
| EMERGENCY | 좌석 밖 쓰러진 승객, 의식불명 의심 | 즉시 정차 + 119 자동 신고 |
| VULNERABLE | 휠체어 / 유모차 탑승 | 슬로프 자동 전개 |
| NORMAL | 정상 착석, 수면, 불확실한 모든 경우 | 없음 |

오탐 방지 원칙: 판단이 불확실한 경우 반드시 NORMAL로 처리.

## Features

- 이미지 전처리: PIL로 1024px 리사이즈 후 Base64 인코딩
- GPS 역지오코딩: OpenStreetMap Nominatim으로 위경도 → 한국어 주소 변환 (비동기)
- 119 신고 텍스트 자동 생성 (버스 ID + 주소 + 상황 설명 포함)
- Leaflet.js 기반 실시간 버스 위치 지도 시뮬레이션 (수원 30번 실제 정류장 GPS)
- 다중 이미지 배치 분석: 버스 이동 중 백그라운드 스레드 병렬 처리

## API

```
POST /analyze
  image   : UploadFile (jpg/png)
  lat     : float
  lng     : float
  bus_id  : str

Response
  situation_type  : EMERGENCY | VULNERABLE | NORMAL
  action          : STOP_IMMEDIATELY | DEPLOY_SLOPE | NONE
  description     : str
  confidence      : float (0.0 ~ 1.0)
  emergency_report: str | null
  address         : str
```

## Tech Stack

- FastAPI, uvicorn, Python
- Groq API — meta-llama/llama-4-scout-17b-16e-instruct
- Streamlit (데모 UI)
- Leaflet.js, OpenStreetMap Nominatim
- Pillow, python-dotenv

## Run

```bash
pip install -r requirements.txt

# .env
GROQ_API_KEY=your_api_key

# 백엔드
python main.py

# 데모 UI (새 터미널)
streamlit run demo.py
```

## Test Data

유사 환경 이미지 (Unsplash/Pexels CC0): 응급상황 5장 / 교통약자 6장 / 정상 3장
