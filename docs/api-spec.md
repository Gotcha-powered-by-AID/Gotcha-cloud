# Gotcha Cloud API 명세서

## 1. 메타데이터 처리 API

### Endpoint
```
POST /process_metadata
```

### 설명  
S3에 업로드된 이미지의 메타데이터를 처리하고, 데이터베이스에 저장합니다.

### Request Body
| 필드           | 타입        | 필수 여부 | 설명                          |
|----------------|------------|----------|-------------------------------|
| device_id      | string     | 필수     | 업로드 기기의 고유 ID         |
| latitude       | float      | 필수     | 이미지의 GPS 위도             |
| longitude      | float      | 필수     | 이미지의 GPS 경도             |
| capture_time   | string     | 필수     | 이미지 촬영 시간 (YYYY-MM-DD HH:MM:SS) |
| image_url      | string     | 필수     | S3에 저장된 원본 이미지 URL   |
| cropped_url    | string     | 선택     | 크롭된 이미지 URL             |
| plate_string   | string     | 선택     | 추출된 차량 번호판 문자열     |

### Request 예시
```json
{
  "device_id": "device_001",
  "latitude": 37.123456,
  "longitude": 127.123456,
  "capture_time": "2024-06-12 12:00:00",
  "image_url": "https://example.com/image1.jpg",
  "cropped_url": "https://example.com/cropped1.jpg",
  "plate_string": "123ABC"
}
```

### Response
| 필드          | 타입       | 설명                         |
|---------------|-----------|------------------------------|
| status        | string    | 요청 처리 상태 ("success")    |
| message       | string    | 상태 메시지                  |

### Response 예시
```json
{
  "status": "success",
  "message": "Metadata processed and stored successfully."
}
```

---

## 2. 배경 분석 API

### Endpoint
```
POST /compare_background
```

### 설명  
두 이미지의 배경을 비교하고 유사도 값을 반환합니다.

### Request Body
| 필드              | 타입        | 필수 여부 | 설명                          |
|-------------------|------------|----------|-------------------------------|
| first_cropped_url | string     | 필수     | 첫 번째 이미지의 URL          |
| second_cropped_url| string     | 필수     | 두 번째 이미지의 URL          |

### Request 예시
```json
{
  "first_cropped_url": "https://example.com/cropped1.jpg",
  "second_cropped_url": "https://example.com/cropped2.jpg"
}
```

### Response
| 필드          | 타입       | 설명                         |
|---------------|-----------|------------------------------|
| similarity    | float     | 두 이미지 간 유사도 (0 ~ 1)   |
| report_id     | string    | 처리된 리포트 ID (선택사항)   |

### Response 예시
```json
{
  "similarity": 0.85,
  "report_id": "report_001"
}
```

---

## 응답 코드 (Status Codes)

| 코드 | 설명                                  |
|------|---------------------------------------|
| 200  | 요청이 성공적으로 처리됨              |
| 400  | 잘못된 요청 (필수 필드 누락 등)       |
| 500  | 서버 내부 오류                        |

---

## 기타 사항
- **보안**: API 요청은 인증된 클라이언트만 접근할 수 있도록 AWS IAM 정책 또는 API Gateway 인증을 적용할 것을 권장합니다.
- **환경 변수**: EC2 서버와 RDS 접속 정보는 환경 변수 또는 AWS Secrets Manager에서 관리합니다.
