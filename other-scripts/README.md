# Yelp Scraper & DynamoDB Upload Scripts

This folder contains scripts and data used to scrape restaurant information from Yelp for multiple cuisines and upload the data to an AWS DynamoDB table.

## Files in this folder

- **`yelp_scraper.py`**  
  Scrapes restaurant data from the Yelp API for 10 cuisines in Manhattan, NY.  
  - Cuisines included: Italian, Chinese, Mexican, Indian, Japanese, Thai, Korean, French, Mediterranean, American  
  - Ensures each restaurant is unique (no duplicates).  
  - Fetches approximately 200–400 unique restaurants per cuisine.  
  - Saves all data into **`yelp_data_full.json`**.

- **`upload_yelp_to_dynamo.py`**  
  Uploads the restaurant data from `yelp_data_full.json` to a DynamoDB table (`yelp-restaurants`).  
  - Converts float values to `Decimal` for DynamoDB compatibility.  
  - Uses batch writing for efficient insertion.  
  - Avoids missing primary keys (`business_id`) and prints upload progress every 100 items.

- **`yelp_data_full.json`**  
  JSON file containing all scraped restaurant data.  
  - Total unique restaurants fetched overall: **2849**  
  - Example per cuisine:  
    - Italian: 200  
    - Chinese: 388  
    - Mexican: 365  
    - Indian: 308  
    - Japanese: 347  
    - Thai: 211  
    - Korean: 201  
    - French: 310  
    - Mediterranean: 277  
    - American: 242

- **`yelp_scripts_readme.md`**  
  This documentation file.

## Usage

### 1. Yelp Scraper

1. Install required Python packages:
   ```bash
   pip install requests python-dotenv
   ```
2. Create a `.env` file with your Yelp API key:
   ```env
   YELP_API_KEY=your_yelp_api_key_here
   ```
3. Run the scraper:
   ```bash
   python yelp_scraper.py
   ```
4. The script will generate **`yelp_data_full.json`** with all restaurant data.

### 2. Upload to DynamoDB

1. Install Boto3 if not already installed:
   ```bash
   pip install boto3
   ```
2. Ensure AWS CLI is configured with credentials that can access DynamoDB.
3. Run the upload script:
   ```bash
   python upload_yelp_to_dynamo.py
   ```
4. The script will upload all items from `yelp_data_full.json` to the `yelp-restaurants` table.

## Notes

- The scraper uses a combination of **cuisines** and **Manhattan zip codes** to fetch a broad and diverse dataset.  
- Duplicate restaurants are avoided using the `business_id` field.  
- The DynamoDB table must