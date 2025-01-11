import boto3
import os
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables from a .env file
load_dotenv()

# Configuration
R2_ACCESS_KEY = os.getenv("R2_ACCESS_KEY")
R2_SECRET_KEY = os.getenv("R2_SECRET_KEY")
R2_BUCKET_NAME = os.getenv("R2_BUCKET_NAME")
R2_ENDPOINT_URL = os.getenv("R2_ENDPOINT_URL")

# Initialize the S3 client for Cloudflare R2
s3_client = boto3.client(
    "s3",
    aws_access_key_id=R2_ACCESS_KEY,
    aws_secret_access_key=R2_SECRET_KEY,
    endpoint_url=R2_ENDPOINT_URL,
)

# Determine file type based on extension
def determine_content_type(file_name):
    if file_name.lower().endswith(('.jpg', '.jpeg', '.png', '.gif')):
        return "image/jpeg"
    elif file_name.lower().endswith('.mp4'):
        return "video/mp4"
    elif file_name.lower().endswith('.avi'):
        return "video/x-msvideo"
    elif file_name.lower().endswith('.mov'):
        return "video/quicktime"
    else:
        return "application/octet-stream"

# Extract date from the directory structure
def extract_date_from_path(file_key):
    try:
        parts = file_key.split("/")
        if len(parts) >= 3:
            year = parts[0]
            month = parts[1]
            day = parts[2]
            month_number = datetime.strptime(month, "%B").month
            return f"{year}-{month_number:02d}-{int(day):02d}"
        else:
            return None
    except Exception as e:
        print(f"Error extracting date from path '{file_key}': {e}")
        return None

# Update metadata and content type
def update_metadata_with_correct_type(bucket_name):
    try:
        paginator = s3_client.get_paginator("list_objects_v2")
        for page in paginator.paginate(Bucket=bucket_name):
            for obj in page.get("Contents", []):
                key = obj["Key"]
                print(f"Processing object: {key}")

                update_date = extract_date_from_path(key)
                if not update_date:
                    print(f"Could not determine date for object: {key}")
                    continue

                content_type = determine_content_type(key)
                file_type = "image" if "image" in content_type else "video"

                head_response = s3_client.head_object(Bucket=bucket_name, Key=key)
                current_metadata = head_response.get("Metadata", {})

                new_metadata = {
                    **current_metadata,
                    "update-date": update_date,
                    "file-type": file_type
                }

                s3_client.copy_object(
                    Bucket=bucket_name,
                    CopySource={"Bucket": bucket_name, "Key": key},
                    Key=key,
                    Metadata=new_metadata,
                    MetadataDirective="REPLACE",
                    ContentType=content_type,
                )
                print(f"Updated metadata and content type for object: {key}")

    except Exception as e:
        print(f"Error updating metadata: {e}")

if __name__ == "__main__":
    update_metadata_with_correct_type(R2_BUCKET_NAME)
