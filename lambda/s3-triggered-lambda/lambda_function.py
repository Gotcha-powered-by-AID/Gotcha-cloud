import json
import boto3
from PIL import Image
import piexif
import requests
import uuid
from datetime import datetime

s3 = boto3.client('s3')

def rational_to_float(rational):
    return rational[0] / rational[1]

def extract_metadata(file_path):
    image = Image.open(file_path)
    exif_data = piexif.load(image.info['exif'])
    metadata = {}

    metadata['device_id'] = str(uuid.uuid4())
    
    
    if 'GPS' in exif_data:
        gps_info = exif_data['GPS']
        if piexif.GPSIFD.GPSLatitude in gps_info and piexif.GPSIFD.GPSLatitudeRef in gps_info:
            lat = gps_info[piexif.GPSIFD.GPSLatitude]
            metadata['latitude'] = round(sum([rational_to_float(val) / 60 ** i for i, val in enumerate(lat)]), 6)

        if piexif.GPSIFD.GPSLongitude in gps_info and piexif.GPSIFD.GPSLongitudeRef in gps_info:
            lon = gps_info[piexif.GPSIFD.GPSLongitude]
            metadata['longitude'] = round(sum([rational_to_float(val) / 60 ** i for i, val in enumerate(lon)]), 6)
        
        if 'Exif' in exif_data and piexif.ExifIFD.DateTimeOriginal in exif_data['Exif']:
            capture_time_str = exif_data['Exif'][piexif.ExifIFD.DateTimeOriginal].decode('utf-8')
            capture_time = datetime.strptime(capture_time_str, "%Y:%m:%d %H:%M:%S")
            metadata['capture_time'] = capture_time.strftime('%Y-%m-%d %H:%M:%S')
    
    metadata['cropped_url'] = None
    metadata['plate_string'] = None

    return metadata

def lambda_handler(event, context):
    read_bucket = 'capstone-raw-image-bucket'
    key = event['Records'][0]['s3']['object']['key']
    download_path = f'/tmp/{key}'
    
    try:
        s3.download_file(read_bucket, key, download_path)
    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps(f"Error downloading file from S3: {str(e)}")
        }

    try:
        metadata = extract_metadata(download_path)
    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps(f"Error extracting metadata: {str(e)}")
        }

    s3_url = f's3://{read_bucket}/{key}'
    metadata['image_url'] = s3_url

    ec2_url = f'http://43.203.171.209:5000/process_metadata'
    response = requests.post(ec2_url, json=metadata)

    return {
        'statusCode': 200,
        'body': json.dumps('Metadata extracted and sent to EC2.')
    }