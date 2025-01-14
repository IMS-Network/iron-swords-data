import csv
from playwright.sync_api import sync_playwright

# Define a function to extract casualty data from the details page
def extract_casualty_data(page):
    try:
        name = page.query_selector('h1.heading-default.h1-heading').inner_text().strip()
        division = page.query_selector('div.tag-text').inner_text().strip()
        date_fallen = page.query_selector('p:has-text("נפל")').inner_text().strip()
        description = page.query_selector('div.media-body p:nth-of-type(2)').inner_text().strip()
        english_name = description.split('z"l')[-1].strip()

        # Extract the image URL
        image_element = page.query_selector('div.soldier-image img.img-fluid')  # Selector for the image
        raw_image_url = image_element.get_attribute('src') if image_element else None

        # Process the image URL to remove query strings and add base URL
        if raw_image_url:
            base_url = "https://idf.il"
            clean_image_url = raw_image_url.split('?')[0]  # Remove query strings
            full_image_url = f"{base_url}{clean_image_url}"  # Add base URL
        else:
            full_image_url = None

        return {
            "name": name,
            "division": division,
            "date_fallen": date_fallen,
            "description": description,
            "english_name": english_name,
            "image_url": full_image_url  # Include the full image URL
        }
    except Exception as e:
        print(f"Error extracting data: {e}")
        return None

# Function to scrape data for each page and each soldier
def scrape_idf_casualties():
    with sync_playwright() as p:
        # Start the browser
        browser = p.chromium.launch(headless=False)  # Set headless=True if you don't need the browser UI
        page = browser.new_page()

        # Initialize the CSV file with headers
        with open('heroes.csv', 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = ['name', 'division', 'date_fallen', 'description', 'english_name', 'image_url']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()

        page_number = 1

        while True:
            # Go to the current page of the casualties list
            list_page_url = f"https://www.idf.il/%D7%A0%D7%95%D7%A4%D7%9C%D7%99%D7%9D/%D7%97%D7%9C%D7%9C%D7%99-%D7%94%D7%9E%D7%9C%D7%97%D7%9E%D7%94/?page={page_number}"
            page.goto(list_page_url)
            page.wait_for_load_state("load")

            print(f"Scraping page {page_number}...")

            # Get all soldier listings on the page
            soldier_listings = page.query_selector_all('.col-lg-6.col-md-6.wrap-item')

            if not soldier_listings:
                print(f"No more soldiers found on page {page_number}. Stopping.")
                break

            # Loop through each soldier listing
            for index in range(len(soldier_listings)):
                try:
                    soldier_listings = page.query_selector_all('.col-lg-6.col-md-6.wrap-item')
                    soldier_listings[index].query_selector('span.btn-link-text').click()
                    page.wait_for_load_state("load")

                    # Extract data from the soldier's personal page
                    casualty_data = extract_casualty_data(page)

                    if casualty_data:
                        print(f"Soldier: {casualty_data['english_name']} - added to data")

                        # Append data to the CSV file
                        with open('heroes.csv', 'a', newline='', encoding='utf-8') as csvfile:
                            fieldnames = ['name', 'division', 'date_fallen', 'description', 'english_name', 'image_url']
                            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                            writer.writerow(casualty_data)

                    # Navigate back to the current page
                    page.goto(list_page_url)
                    page.wait_for_load_state("load")

                except Exception as e:
                    print(f"Error navigating or extracting data for soldier {index + 1} on page {page_number}: {e}")

            # Check for the "Next" button
            next_page_link = page.query_selector('.pagination .page-link[rel="next"]')
            if next_page_link:
                next_page_link.click()  # Click the "Next" button
                page.wait_for_load_state("load")  # Wait for the next page to load
                page_number += 1  # Increment the page counter
            else:
                print("No more pages. Scraping completed.")
                break

        # Close the browser
        browser.close()

        print("Data successfully written to heroes.csv")

# Run the scraper
scrape_idf_casualties()
