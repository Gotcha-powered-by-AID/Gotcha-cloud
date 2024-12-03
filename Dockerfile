FROM ubuntu:22.04

# 필요한 패키지 설치
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    libgl1 \
    libglib2.0-0 \
    && apt-get clean

# requirements.txt 파일을 복사하고 패키지 설치
COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt

# 앱 소스 코드 복사
COPY . .

# 애플리케이션 실행
CMD ["python3", "app.py"]