from flask import Flask, request, jsonify
import boto3
import pymysql
import cv2
import re
import json
import os
import io
import logging
from ultralytics import YOLO
from paddleocr import PaddleOCR
from PIL import Image
from scipy.spatial import distance
from tensorflow.keras.applications import ResNet50
from tensorflow.keras.preprocessing import image
from tensorflow.keras.applications.resnet50 import preprocess_input
import numpy as np

app = Flask(__name__)
s3 = boto3.client('s3')

# 모델 로딩 (YOLO 및 ResNet50)
model = YOLO('yolov9c.pt')
ocr = PaddleOCR(lang="korean")
base_model = ResNet50(weights='imagenet', include_top=False, pooling='avg')

# RDS 연결 함수
def get_db_connection():
    return pymysql.connect(
        host="capstone-aid-database.c3seym2oyyq4.ap-northeast-2.rds.amazonaws.com",
        user="aid2024",
        password="Awsaid2024!!",
        database="gotcha_db"
    )

# S3에서 이미지 다운로드 함수
def download_image_from_s3(bucket_name, object_key):
    download_path = f"/tmp/{object_key.split('/')[-1]}"
    try:
        s3.download_file(bucket_name, object_key, download_path)
        return download_path
    except Exception as e:
        logging.error(f"Error downloading image from S3: {str(e)}")
        raise

# 임시 테이블에 메타데이터 삽입 함수
def insert_metadata_into_rds(data):
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            sql = """
            INSERT INTO temporary (device_id, capture_time, latitude, longitude, image_url, plate_string, cropped_url)
            VALUES (%s, %s, %s, %s, %s, %s, %s);
            """
            cursor.execute(sql, (
                data['device_id'],
                data['capture_time'],
                data['latitude'],
                data['longitude'],
                data['image_url'],
                data['plate_string'],
                data['cropped_url']
            ))
            connection.commit()
    except Exception as e:
        logging.error(f"Error inserting data into RDS: {e}")
    finally:
        connection.close()

# YOLO와 PaddleOCR를 사용하여 차량 번호판 추출 함수
def extract_plate(image_path):
    ALLOWED_OBJECTS = ['car', 'truck']
    image = cv2.imread(image_path)
    if image is None:
        logging.error("Failed to load image.")
        return None, None

    # 차량 탐지 및 트래킹
    results = model.track(image, persist=True, verbose=False)
    detections = json.loads(results[0].tojson())

    max_confidence = 0
    best_detection = None
    for det in detections:
        if 'track_id' not in det:
            continue
        class_name = det['name']
        if class_name not in ALLOWED_OBJECTS:
            continue
        conf = det['confidence']
        if conf > max_confidence:
            max_confidence = conf
            best_detection = det

    if best_detection:
        box = best_detection['box']
        x1, y1, x2, y2 = int(box['x1']), int(box['y1']), int(box['x2']), int(box['y2'])
        car_s = image[y1:y2, x1:x2]
        car_m = image[y1-300:y2+100, x1-300:x2+300]

        # OCR을 통해 번호판 텍스트 추출
        result = ocr.ocr(car_s, cls=False)
        text_result = []
        for line in result[0]:
            text_result.append(line[1][0])
        final_result = ''.join(text_result)

        # 정규식을 이용하여 번호판 패턴 매칭
        kopt = '가나다라마거너더러머고노도로모구누두루무버서어저보소오조부수우주허하호'
        pattern = re.compile(fr'\d{{2,3}}[{kopt}]\d{{4}}')
        plate = pattern.findall(final_result)
        return car_m, plate

    return None, None

# ResNet50을 사용하여 이미지에서 특성 추출
def extract_features(img_path):
    img = image.load_img(img_path, target_size=(224, 224))
    img_data = image.img_to_array(img)
    img_data = np.expand_dims(img_data, axis=0)
    img_data = preprocess_input(img_data)
    features = base_model.predict(img_data)
    return features.flatten()

# 배경 유사도 비교 함수
def background_comparison(image_path1, image_path2):
    features1 = extract_features(image_path1)
    features2 = extract_features(image_path2)
    similarity = 1 - distance.cosine(features1, features2)
    return similarity

# process_metadata API 라우트
@app.route('/process_metadata', methods=['POST'])
def process_metadata():
    data = request.json
    image_url = data['image_url']
    bucket_name = image_url.split('/')[2]
    object_key = '/'.join(image_url.split('/')[3:])
    
    try:
        image_path = download_image_from_s3(bucket_name, object_key)
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"Failed to download image: {str(e)}"
        }), 500

    car_m, plate = extract_plate(image_path)
    if car_m is None or plate is None:
        return jsonify({
            "status": "error",
            "message": "Failed to extract license plate or process image."
        }), 500

    car_m = cv2.cvtColor(car_m, cv2.COLOR_BGR2RGB)
    image = Image.fromarray(car_m)
    img_byte_arr = io.BytesIO()
    image.save(img_byte_arr, format='JPEG')
    img_byte_arr.seek(0)
    processed_bucket = 'capstone-processed-image-bucket'
    s3_key = f'{data["device_id"]}.jpg'
    try:
        s3.upload_fileobj(img_byte_arr, processed_bucket, s3_key)
        cropped_url = f's3://{processed_bucket}/{s3_key}'
        data['cropped_url'] = cropped_url
        data['plate_string'] = plate
        insert_metadata_into_rds(data)
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"Failed to upload processed image to S3: {str(e)}"
        }), 500

    return jsonify({
        "status": "success",
        "processed_data": data,
        "plate": plate,
        "cropped_url": cropped_url
    }), 200

# compare_background API 라우트
@app.route('/compare_background', methods=['POST'])
def compare_background():
    data = request.json
    first_cropped_url = data["first_cropped_url"]
    second_cropped_url = data["second_cropped_url"]

    bucket_name = "capstone-processed-image-bucket"

    # 오브젝트 키 추출
    object_key1 = first_cropped_url.split('/', 3)[-1]
    object_key2 = second_cropped_url.split('/', 3)[-1]

    try:
        # 오브젝트 키로 이미지 다운로드
        image_path1 = download_image_from_s3(bucket_name, object_key1)
        image_path2 = download_image_from_s3(bucket_name, object_key2)
        similarity = background_comparison(image_path1, image_path2)

        return jsonify({"similarity": similarity}), 200

    except Exception as e:
        logging.error(f"Error in background comparison: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)