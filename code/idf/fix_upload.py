import pymysql
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

# Default _wpml_word_count value
default_wpml_word_count = '{"total":562,"to_translate":{"en":562,"ru":562}}'

# Function to add _wpml_word_count metadata to missing posts
def add_wpml_word_count():
    try:
        # Connect to the database
        connection = pymysql.connect(**db_config)
        with connection.cursor() as cursor:
            # Find all posts missing _wpml_word_count
            find_missing_query = """
            SELECT p.ID
            FROM 9v533_posts p
            LEFT JOIN 9v533_postmeta pm ON p.ID = pm.post_id AND pm.meta_key = '_wpml_word_count'
            WHERE p.post_type = 'at_biz_dir' AND pm.meta_id IS NULL;
            """
            cursor.execute(find_missing_query)
            missing_posts = cursor.fetchall()

            # Add _wpml_word_count for each missing post
            for post in missing_posts:
                post_id = post[0]
                insert_query = """
                INSERT INTO 9v533_postmeta (post_id, meta_key, meta_value)
                VALUES (%s, '_wpml_word_count', %s)
                """
                cursor.execute(insert_query, (post_id, default_wpml_word_count))
                print(f"Added _wpml_word_count for post ID {post_id}")

            # Commit changes
            connection.commit()
            print("Successfully added _wpml_word_count for all missing posts.")
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        if connection:
            connection.close()

# Run the script
if __name__ == "__main__":
    add_wpml_word_count()
