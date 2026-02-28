import boto3
import json
from decimal import Decimal

dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
table = dynamodb.Table('yelp-restaurants')

with open("yelp_data_full.json", "r") as f:
    data = json.load(f)

def convert_numbers(item):
    if isinstance(item, dict):
        return {k: convert_numbers(v) for k, v in item.items()}
    elif isinstance(item, list):
        return [convert_numbers(v) for v in item]
    elif isinstance(item, float):
        return Decimal(str(item))
    else:
        return item

uploaded_count = 0
with table.batch_writer() as batch:
    for i, restaurant in enumerate(data, 1):
        if 'business_id' not in restaurant:  # business_id is primary key
            print(f"Skipping item {i}: missing business_id")
            continue
        batch.put_item(Item=convert_numbers(restaurant))
        uploaded_count += 1
        if uploaded_count % 100 == 0:
            print(f"Uploaded {uploaded_count}/{len(data)} items...")

print(f"✅ Uploaded {uploaded_count} items to DynamoDB!")
