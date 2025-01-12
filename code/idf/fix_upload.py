import pymysql
import os
import json
import re
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

# Exclude specific post IDs
excluded_ids = [466, 315, 332, 95, 64, 382, 336, 426, 454]

# Function to calculate word count
def calculate_word_count(text):
    if not text:
        return 0
    # Remove HTML tags and count words
    clean_text = re.sub(r'<[^>]+>', '', text)
    return len(clean_text.split())

# Function to fetch posts and update _wpml_word_count
def recount_and_update_word_count():
    try:
        # Connect to the database
        connection = pymysql.connect(**db_config)
        with connection.cursor() as cursor:
            # Fetch posts except the excluded ones
            find_posts_query = f"""
            SELECT p.ID, p.post_content
            FROM 9v533_posts p
            WHERE p.post_type = 'at_biz_dir' AND p.ID NOT IN ({','.join(map(str, excluded_ids))});
            """
            cursor.execute(find_posts_query)
            posts = cursor.fetchall()

            for post in posts:
                post_id = post[0]
                post_content = post[1]

                # Calculate word count
                word_count = calculate_word_count(post_content)

                # Create _wpml_word_count value
                wpml_word_count = {
                    "total": word_count,
                    "to_translate": {
                        "en": word_count,
                        "ru": word_count,
                    },
                }
                wpml_word_count_json = json.dumps(wpml_word_count, ensure_ascii=False)

                # Insert or update _wpml_word_count metadata
                insert_query = """
                INSERT INTO 9v533_postmeta (post_id, meta_key, meta_value)
                VALUES (%s, '_wpml_word_count', %s)
                ON DUPLICATE KEY UPDATE meta_value = VALUES(meta_value);
                """
                cursor.execute(insert_query, (post_id, wpml_word_count_json))
                print(f"Updated _wpml_word_count for post ID {post_id} with {wpml_word_count_json}")

            # Commit changes
            connection.commit()
            print("Successfully updated _wpml_word_count for all relevant posts.")
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        if connection:
            connection.close()

# Run the script
if __name__ == "__main__":
    recount_and_update_word_count()
