import pymysql
import csv
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Database connection details
db_config = {
    "host": os.getenv("DB_HOST", "localhost"),
    "user": os.getenv("DB_USER", "root"),
    "password": os.getenv("DB_PASSWORD", ""),
    "database": os.getenv("DB_NAME", "iron-swords-heroes"),
    "port": int(os.getenv("DB_PORT", 3306)),
    "charset": "utf8mb4",
}

# CSV file path
csv_file_path = os.getenv("CSV_FILE_PATH", "/mnt/data/heroes_corrected.csv")

# Helper function to execute SQL queries
def execute_query(cursor, query, params):
    try:
        cursor.execute(query, params)
    except Exception as e:
        print(f"Query failed: {query}\nParams: {params}\nError: {e}")
        raise

# Function to insert post data into WordPress
def insert_post(cursor, post_data):
    post_query = (
        "INSERT INTO 9v533_posts (post_author, post_date, post_date_gmt, post_content, post_title, "
        "post_excerpt, post_status, comment_status, ping_status, post_name, post_type, post_modified, "
        "post_modified_gmt, to_ping, pinged, post_content_filtered) "
        "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
    )
    post_content = post_data.get("description", "").strip()  # Map description to post_content
    post_title = post_data.get("name", "").strip()  # Map name to post_title
    slug = post_title.replace(" ", "-").lower()  # Generate slug from the title

    print(f"Inserting post with title: {post_title}, content: {post_content}")

    params = (
        3,  # post_author
        post_data["formatted_fallen_date"],  # post_date
        post_data["formatted_fallen_date"],  # post_date_gmt
        post_content,  # post_content
        post_title,  # post_title
        "",  # post_excerpt
        "publish",  # post_status
        "open",  # comment_status
        "closed",  # ping_status
        slug,  # post_name (slug)
        "at_biz_dir",  # post_type
        post_data["formatted_fallen_date"],  # post_modified
        post_data["formatted_fallen_date"],  # post_modified_gmt
        "",  # to_ping
        "",  # pinged
        "",  # post_content_filtered
    )

    execute_query(cursor, post_query, params)
    return cursor.lastrowid

# Function to insert post metadata
def insert_metadata(cursor, post_id, meta_key, meta_value):
    meta_query = "INSERT INTO 9v533_postmeta (post_id, meta_key, meta_value) VALUES (%s, %s, %s)"
    execute_query(cursor, meta_query, (post_id, meta_key, meta_value))

# Main script
try:
    connection = pymysql.connect(**db_config)
    with connection.cursor() as cursor:
        with open(csv_file_path, "r", encoding="utf-8") as file:
            reader = csv.DictReader(file)
            for row in reader:
                # Insert post
                post_id = insert_post(cursor, row)

                # Insert metadata
                metadata = {
                    "_custom-date": row["formatted_fallen_date"],
                    "_custom-number": row["custom-number"],
                    "_directory_type": 2,
                    "_never_expire": 1,
                    "_listing_status": "post_status",
                }
                for key, value in metadata.items():
                    insert_metadata(cursor, post_id, key, value)

        connection.commit()

except Exception as e:
    print(f"An error occurred: {e}")

finally:
    if connection:
        connection.close()

print("Data import complete.")
