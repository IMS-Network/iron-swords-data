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
    cursor.execute(query, params)

# Function to create taxonomy terms if they don't exist
def create_taxonomy_term(cursor, term_name, taxonomy):
    # Check if the term already exists
    term_check_query = (
        "SELECT term_id FROM 9v533_terms WHERE name = %s AND term_id IN "
        "(SELECT term_id FROM 9v533_term_taxonomy WHERE taxonomy = %s)"
    )
    cursor.execute(term_check_query, (term_name, taxonomy))
    term = cursor.fetchone()

    if not term:
        # Insert the term into 9v533_terms
        insert_term_query = "INSERT INTO 9v533_terms (name, slug) VALUES (%s, %s)"
        term_slug = term_name.replace(" ", "-").lower()
        cursor.execute(insert_term_query, (term_name, term_slug))
        term_id = cursor.lastrowid

        # Associate the term with the taxonomy in 9v533_term_taxonomy
        insert_taxonomy_query = (
            "INSERT INTO 9v533_term_taxonomy (term_id, taxonomy) VALUES (%s, %s)"
        )
        cursor.execute(insert_taxonomy_query, (term_id, taxonomy))
        return term_id
    else:
        # Return the existing term_id
        return term["term_id"]

# Function to insert post data into WordPress
def insert_post(cursor, post_data):
    post_query = (
        "INSERT INTO 9v533_posts (post_author, post_date, post_date_gmt, post_content, post_title, "
        "post_status, comment_status, ping_status, post_name, post_type, post_modified, post_modified_gmt) "
        "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
    )
    cursor.execute(
        post_query,
        (
            3,  # post_author
            post_data["formatted_fallen_date"],
            post_data["formatted_fallen_date"],
            post_data["description"],
            post_data["name"],
            "publish",  # post_status
            "open",  # comment_status
            "closed",  # ping_status
            post_data["slug"],
            "at_biz_dir",  # post_type
            post_data["formatted_fallen_date"],  # post_modified
            post_data["formatted_fallen_date"],  # post_modified_gmt
        ),
    )
    return cursor.lastrowid

# Function to insert post metadata
def insert_metadata(cursor, post_id, meta_key, meta_value):
    meta_query = "INSERT INTO 9v533_postmeta (post_id, meta_key, meta_value) VALUES (%s, %s, %s)"
    execute_query(cursor, meta_query, (post_id, meta_key, meta_value))

# Function to associate taxonomies
def associate_taxonomy(cursor, post_id, taxonomy_data):
    for term_name, taxonomy in taxonomy_data:
        # Create the taxonomy term if it doesn't exist
        term_id = create_taxonomy_term(cursor, term_name, taxonomy)
        
        # Associate the term with the post
        term_relationship_query = (
            "INSERT INTO 9v533_term_relationships (object_id, term_taxonomy_id) "
            "SELECT %s, term_taxonomy_id FROM 9v533_term_taxonomy WHERE term_id = %s"
        )
        execute_query(cursor, term_relationship_query, (post_id, term_id))

# Main script
try:
    connection = pymysql.connect(**db_config)
    with connection.cursor() as cursor:
        with open(csv_file_path, "r", encoding="utf-8") as file:
            reader = csv.DictReader(file)
            for row in reader:
                # Generate slug from name
                row["slug"] = row["name"].replace(" ", "-").lower()

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

                # Associate taxonomies
                taxonomy_data = [
                    (row["division"], "at_biz_dir-category"),
                    (row["location"], "at_biz_dir-location"),
                    ("חיילים", "atbdp_listing_types"),
                    (row["tag"], "at_biz_dir-tags"),
                ]
                associate_taxonomy(cursor, post_id, taxonomy_data)

        # Commit changes
        connection.commit()

except Exception as e:
    print(f"An error occurred: {e}")

finally:
    if connection:
        connection.close()

print("Data import complete.")
