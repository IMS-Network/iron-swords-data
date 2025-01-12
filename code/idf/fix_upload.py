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

# Function to update GUIDs
def update_guids():
    try:
        # Connect to the database
        connection = pymysql.connect(**db_config)
        with connection.cursor() as cursor:
            # Select posts that need GUID updates
            select_query = """
            SELECT ID, post_name
            FROM 9v533_posts
            WHERE post_type = 'at_biz_dir' AND guid LIKE 'https://heroes.iron-swords.co.il/?p=%';
            """
            cursor.execute(select_query)
            posts = cursor.fetchall()

            # Update GUIDs for each post
            for post in posts:
                post_id, post_name = post
                new_guid = f"https://heroes.iron-swords.co.il/directory/{post_name}/"
                update_query = "UPDATE 9v533_posts SET guid = %s WHERE ID = %s;"
                cursor.execute(update_query, (new_guid, post_id))
                print(f"Updated GUID for post ID {post_id} to {new_guid}")

            # Commit the changes
            connection.commit()
            print("All GUIDs have been updated successfully.")
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        if connection:
            connection.close()

# Run the update function
if __name__ == "__main__":
    update_guids()
