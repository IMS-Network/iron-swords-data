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

# Function to create taxonomy terms if they don't exist
def create_taxonomy_term(cursor, term_name, taxonomy):
    if not term_name:
        return  # Skip empty taxonomy terms
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
        return term[0]

# Function to associate taxonomy terms with a post
def associate_taxonomy(cursor, post_id, taxonomy_data):
    for term_name, taxonomy in taxonomy_data:
        if not term_name:
            continue  # Skip empty terms
        term_id = create_taxonomy_term(cursor, term_name, taxonomy)
        term_relationship_query = (
            "INSERT INTO 9v533_term_relationships (object_id, term_taxonomy_id) "
            "SELECT %s, term_taxonomy_id FROM 9v533_term_taxonomy WHERE term_id = %s"
        )
        execute_query(cursor, term_relationship_query, (post_id, term_id))

# Function to insert post data into WordPress
def insert_post(cursor, post_data):
    post_query = (
        "INSERT INTO 9v533_posts (post_author, post_date, post_date_gmt, post_content, post_title, "
        "post_excerpt, post_status, comment_status, ping_status, post_name, post_type, post_modified, "
        "post_modified_gmt, to_ping, pinged, post_content_filtered) "
        "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
    )

    # Explicitly extract and clean data from the CSV row
    post_content = post_data.get("description", "").strip()  # Map description to post_content
    if not post_content:
        post_content = "No description provided."  # Fallback for empty descriptions
    post_title = post_data.get("name", "").strip()  # Map name to post_title
    slug = post_title.replace(" ", "-").lower()  # Generate slug from the title

    # Debug information
    print(f"Inserting post with title: {post_title}, content: {post_content}")

    params = (
        3,  # post_author
        post_data["formatted_fallen_date"],  # post_date
        post_data["formatted_fallen_date"],  # post_date_gmt
        post_content,  # post_content (correctly mapped from CSV description)
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

                # Associate taxonomies
                taxonomy_data = [
                    ("חיילים", "atbdp_listing_types"),  # Fixed for all posts
                    (row.get("division", "").strip(), "at_biz_dir-category"),
                    (row.get("location", "").strip(), "at_biz_dir-location"),
                    (row.get("tag", "").strip(), "at_biz_dir-tags"),
                ]
                associate_taxonomy(cursor, post_id, taxonomy_data)

        connection.commit()

except Exception as e:
    print(f"An error occurred: {e}")

finally:
    if connection:
        connection.close()

print("Data import complete.")
