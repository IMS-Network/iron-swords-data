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

# List of working post IDs
working_posts = [64, 95, 315, 332, 336, 382, 426, 454, 466]

def add_missing_language_associations():
    try:
        connection = pymysql.connect(**db_config)
        with connection.cursor() as cursor:
            # Find posts missing language associations
            find_missing_query = f"""
            SELECT p.ID
            FROM 9v533_posts p
            LEFT JOIN 9v533_icl_translations t ON p.ID = t.element_id
            WHERE p.post_type = 'at_biz_dir' 
              AND t.element_id IS NULL
              AND p.ID NOT IN ({','.join(map(str, working_posts))});
            """
            cursor.execute(find_missing_query)
            missing_posts = cursor.fetchall()

            # Insert language associations for missing posts
            for post in missing_posts:
                post_id = post[0]
                # Get the next TRID
                cursor.execute("SELECT MAX(trid) + 1 FROM 9v533_icl_translations")
                next_trid = cursor.fetchone()[0] or 1

                insert_query = """
                INSERT INTO 9v533_icl_translations (element_id, element_type, language_code, source_language_code, trid)
                VALUES (%s, %s, %s, %s, %s);
                """
                cursor.execute(insert_query, (post_id, 'post_at_biz_dir', 'he', None, next_trid))
                print(f"Added language association for post ID {post_id} with TRID {next_trid}")

            # Commit changes
            connection.commit()
            print("Successfully added missing language associations.")
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        if connection:
            connection.close()

# Run the script
if __name__ == "__main__":
    add_missing_language_associations()
