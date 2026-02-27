# Yelp Scraper, DynamoDB Upload & OpenSearch Indexing Scripts

This folder contains scripts and data used to:
1) Scrape restaurant information from Yelp for multiple cuisines in Manhattan, NY  
2) Upload the scraped data into an AWS DynamoDB table (`yelp-restaurants`)  
3) Index a lightweight subset (RestaurantID + Cuisine) into Amazon OpenSearch (`restaurants` index)

---

## Files in this folder

### 1) `yelp_scraper.py`
Scrapes restaurant data from the Yelp API for **10 cuisines** in Manhattan, NY.

- Cuisines included: Italian, Chinese, Mexican, Indian, Japanese, Thai, Korean, French, Mediterranean, American  
- Ensures each restaurant is unique (no duplicates) using `business_id`  
- Fetches ~200+ restaurants per cuisine (varies by Yelp availability)  
- Saves output to **`yelp_data_full.json`**

---

### 2) `upload_yelp_to_dynamo.py`
Uploads restaurant data from `yelp_data_full.json` to DynamoDB table **`yelp-restaurants`**.

- Converts float values to `Decimal` (required by DynamoDB)  
- Uses `batch_writer()` for efficient inserts  
- Skips entries missing `business_id`  
- Prints progress every ~100 inserts

---

### 3) `open.py` (OpenSearch Bulk Index Script)
Indexes a **partial dataset** into Amazon OpenSearch:

- Index: `restaurants`
- Fields stored per document:
  - `RestaurantID` (business_id)
  - `Cuisine`
- Uses Bulk API (`/_bulk`)  
- Sets document `_id` = `business_id` so duplicates overwrite instead of creating duplicates  
- Randomly selects up to `MAX_DOCS` unique restaurants from `yelp_data_full.json`

✅ This supports the assignment requirement to store only **RestaurantID + Cuisine** in OpenSearch.

---

### 4) `yelp_data_full.json`
JSON file containing all scraped restaurant data.

Example stats from one run:
- Total unique restaurants fetched: **~2849**
- Approx per cuisine:
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

(Exact counts may vary depending on Yelp results.)

---

### 5) `yelp_scripts_readme.md`
This documentation file.

---

## Usage

## 1) Yelp Scraper

1. Install required packages:
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

4. Output will be saved as:
   - `yelp_data_full.json`

---

## 2) Upload to DynamoDB

1. Install boto3:
   ```bash
   pip install boto3
   ```

2. Configure AWS credentials (AWS CLI):
   ```bash
   aws configure
   ```

3. Run the upload script:
   ```bash
   python upload_yelp_to_dynamo.py
   ```

4. Verify the `yelp-restaurants` table contains items.

---

## 3) Index to OpenSearch (Bulk)

### Prerequisites
- OpenSearch domain is running and accessible
- Index `restaurants` exists (or will be created automatically by bulk indexing)
- If using fine-grained access control (FGAC), you need a valid OpenSearch username/password

### IMPORTANT Security Note (Do NOT commit secrets)
Your `open.py` currently includes credentials (`MASTER_USER` / `MASTER_PASS`).  
**Do not commit passwords to GitHub.** Use environment variables instead.

Recommended approach:
- Set in terminal (Mac/Linux):
  ```bash
  export OS_USER="your_user"
  export OS_PASS="your_password"
  ```
- Then read them in code (optional improvement).

### Run the OpenSearch bulk index
1. Install requirements:
   ```bash
   pip install requests
   ```

2. Run:
   ```bash
   python open.py
   ```

3. You should see progress like:
   ```
   Indexed 200/1000
   Indexed 400/1000
   ...
   ✅ Done! Bulk upload completed.
   ```

---

## Notes
- The scraper uses cuisines + Manhattan coverage to build a diverse dataset.
- Duplicates are avoided using Yelp `business_id`.
- DynamoDB stores full restaurant records.
- OpenSearch stores only lightweight fields: **RestaurantID + Cuisine**, as required.
