-- temporary 테이블 생성
CREATE TABLE IF NOT EXISTS temporary (
    report_id INT AUTO_INCREMENT PRIMARY KEY,
    device_id VARCHAR(50),
    capture_time DATETIME NOT NULL,
    latitude DECIMAL(9,6) NOT NULL,
    longitude DECIMAL(9,6) NOT NULL,
    image_url VARCHAR(2048) NOT NULL,
    plate_string VARCHAR(15) NOT NULL,
    cropped_url VARCHAR(2048) NOT NULL
);

-- final 테이블 생성
CREATE TABLE IF NOT EXISTS final (
    report_id VARCHAR(255) PRIMARY KEY,
    plate_string VARCHAR(255),
    first_capture_time VARCHAR(255),
    last_capture_time VARCHAR(255),
    latitude VARCHAR(255),
    longitude VARCHAR(255),
    first_image_url VARCHAR(255),
    last_image_url VARCHAR(255),
    first_device_id VARCHAR(255),
    last_device_id VARCHAR(255),
    first_cropped_url VARCHAR(255),
    second_cropped_url VARCHAR(2048),
    report_bool BIT(1)
);
