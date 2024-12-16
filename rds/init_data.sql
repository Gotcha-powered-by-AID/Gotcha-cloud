-- temporary 테이블 초기 데이터 삽입
INSERT INTO temporary (device_id, capture_time, latitude, longitude, image_url, plate_string, cropped_url)
VALUES
('device_001', '2024-06-12 12:00:00', 37.123456, 127.123456, 'https://example.com/image1.jpg', '123ABC', 'https://example.com/cropped1.jpg'),
('device_002', '2024-06-12 12:05:00', 37.123457, 127.123457, 'https://example.com/image2.jpg', '456DEF', 'https://example.com/cropped2.jpg');

-- final 테이블 초기 데이터 삽입
INSERT INTO final (report_id, plate_string, first_capture_time, last_capture_time, latitude, longitude, first_image_url, last_image_url, first_device_id, last_device_id, first_cropped_url, second_cropped_url, report_bool)
VALUES
('report_001', '123ABC', '2024-06-12 12:00:00', '2024-06-12 12:05:00', '37.123456', '127.123456', 'https://example.com/image1.jpg', 'https://example.com/image2.jpg', 'device_001', 'device_002', 'https://example.com/cropped1.jpg', 'https://example.com/cropped2.jpg', 1);
