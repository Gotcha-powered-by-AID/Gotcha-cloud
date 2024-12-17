import pymysql
import requests
import json
import math
import logging

# RDS와의 연결 설정
def get_db_connection():
    return pymysql.connect(
        host="capstone-aid-database.c3seym2oyyq4.ap-northeast-2.rds.amazonaws.com",
        user="aid2024",
        password="Awsaid2024!!",
        database="gotcha_db"
    )

# 소수점 4자리까지 버림 함수
def truncate_to_four_decimal_places(value):
    return math.trunc(value * 10000)

def lambda_handler(event, context):
    # 데이터베이스 연결 (임시 -> 최종)
    connection = get_db_connection()
    cursor = connection.cursor()

    try:
        # temporary 테이블에서 모든 레코드를 가져옴
        cursor.execute("SELECT report_id, device_id, capture_time, latitude, longitude, image_url, plate_string, cropped_url FROM temporary")
        records = cursor.fetchall()

        # 첫 번째 레코드를 기준으로 처리
        for record in records:
            report_id, device_id, capture_time, latitude, longitude, image_url, plate_string, cropped_url = record

            # 같은 plate_string을 가진 다른 레코드 검색
            cursor.execute("""
                SELECT report_id, device_id, capture_time, latitude, longitude, image_url, cropped_url
                FROM temporary 
                WHERE plate_string = %s AND report_id != %s
                ORDER BY capture_time DESC
                LIMIT 1
            """, (plate_string, report_id))
            
            matching_record = cursor.fetchone()

            if matching_record:
                matched_report_id, matched_device_id, matched_capture_time, matched_latitude, matched_longitude, matched_image_url, matched_cropped_url = matching_record

                # 위도, 경도를 네 자리까지 버림 후 비교
                if (truncate_to_four_decimal_places(latitude) == truncate_to_four_decimal_places(matched_latitude) and 
                    truncate_to_four_decimal_places(longitude) == truncate_to_four_decimal_places(matched_longitude)):
                    # 위도, 경도가 모두 일치하는지 검사
                    time_diff = (matched_capture_time - capture_time).total_seconds()  # 시간 차이 계산 (초 단위)

                    # 시간 간격이 5분 이상인지 확인
                    if time_diff >= 300:
                        report_bool = 0 
                        # final 테이블에 데이터 통합 후 저장
                        cursor.execute("""
                            INSERT INTO final (report_id, plate_string, first_capture_time, last_capture_time, latitude, longitude, first_image_url, last_image_url, first_device_id, last_device_id, first_cropped_url, second_cropped_url, report_bool)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                            ON DUPLICATE KEY UPDATE
                                plate_string = VALUES(plate_string),
                                first_capture_time = VALUES(first_capture_time),
                                last_capture_time = VALUES(last_capture_time),
                                latitude = VALUES(latitude),
                                longitude = VALUES(longitude),
                                first_image_url = VALUES(first_image_url),
                                last_image_url = VALUES(last_image_url),
                                first_device_id = VALUES(first_device_id),
                                last_device_id = VALUES(last_device_id),
                                first_cropped_url = VALUES(first_cropped_url),
                                second_cropped_url = VALUES(second_cropped_url),
                                report_bool = VALUES(report_bool)
                        """, (
                            report_id, plate_string, capture_time, matched_capture_time, latitude, longitude, image_url, matched_image_url, device_id, matched_device_id, cropped_url, matched_cropped_url, report_bool
                        ))

                        # 매칭된 레코드 및 시간 차이 출력
                        print(f"Matched report_id: {report_id} with matched_report_id: {matched_report_id}")
                        print(f"Capture time: {capture_time}, Matched capture time: {matched_capture_time}")
                        print(f"Time difference: {time_diff} seconds")

       # 최종 테이블에 데이터 업데이트 후 커밋
        connection.commit()

        # 배경 분석 진행
        cursor.execute("""
            SELECT report_id, first_cropped_url, second_cropped_url
            FROM final
            WHERE report_bool = 0
        """)
        final_records = cursor.fetchall()

        # 배경 비교
        for final_record in final_records:
            report_id, first_cropped_url, second_cropped_url = final_record
            
            # 배경 분석 API 호출
            ec2_url = f'http://<your-private-ip>:5000/compare_background'
            try:
                response = requests.post(ec2_url, json={
                    "first_cropped_url": first_cropped_url,
                    "second_cropped_url": second_cropped_url
                })

                # 응답이 200이면 similarity 값 추출
                if response.status_code == 200:
                    response_json = response.json()
                    comparison_result = response_json.get("similarity", None)  # "similarity" 키 추출

                    # 유사도 비교 후 report_bool 업데이트
                    if comparison_result is not None:
                        if comparison_result >= 0.8:
                            report_bool = 1  # 유사도 0.8 이상이면 True로 설정
                        else:
                            report_bool = 0  # 유사도 0.8 미만이면 False로 설정
                        
                        # final 테이블에 report_bool 업데이트
                        cursor.execute("""
                            UPDATE final 
                            SET report_bool = %s
                            WHERE report_id = %s
                        """, (report_bool, report_id))

                        logging.info(f"Comparison result for {report_id}: {comparison_result}")
                    else:
                        logging.warning(f"No similarity result for {report_id}")

                else:
                    # API 호출 실패 시 오류 메시지 출력
                    logging.error(f"Error in background comparison for {report_id}, status code: {response.status_code}")

            except Exception as e:
                # API 호출 중 오류 발생 시 오류 메시지 출력
                logging.error(f"Error calling API for {report_id}: {e}")

        # 배경 분석 후 커밋
        connection.commit()

    except Exception as e:
        # 예외 발생 시 롤백
        logging.error(f"Error occurred: {e}")
        connection.rollback()

    finally:
        # 연결 종료
        cursor.close()
        connection.close()

    return {
        'statusCode': 200,
        'body': 'Final 테이블 업데이트 및 배경 분석 완료'
    }
