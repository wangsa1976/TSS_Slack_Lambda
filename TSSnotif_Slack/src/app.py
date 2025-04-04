import json
import os
import urllib3
import boto3
from utils.RU import RU
from datetime import datetime

SLACK_WEBHOOK_URL = os.environ["SLACK_WEBHOOK_URL"]
IN_BUCKET = os.environ['INBUCKET']
TAGID = '411023800'

# Create S3 client 
s3_client = boto3.client('s3')

def data_extract(root_ref: dict, created: str):
    announced_date = root_ref["announced_date"]
    issue = datetime(announced_date["year"], announced_date["month"], announced_date["day"], announced_date["hour"], announced_date["min"]).strftime("%Y%m%d_%H%MZ")
    ICAO = root_ref["ICAO"]
    kind = root_ref["telegram_type"] #NRML/AMND/CRCT
    flighttype = root_ref["flight_type"]  #regular/special
    rev = root_ref["edition"]

    if rev >= 0 and kind == "CRCT":
        message = f"{ICAO} {issue} CRCTed at {created}"
    elif rev == 0 and flighttype == "special":
        message = f"Adhoc REQ {ICAO} {issue} Completed"
    elif rev >= 1 and kind == "AMND":
        if flighttype == "regular":
            message = f"{ICAO} {issue} AMDed at {created}"
        elif flighttype == "special":
            message = f"Adhoc {ICAO} {issue} AMDed at {created}"
    #else:
    #    messagecontent = f"OTHERS: Edition {rev}, {kind} {flighttype} {ICAO} {issue} at {created} is not necessary"
            
    return message

def lambda_handler(event, context):

    # Extract SQS message
    for rec in event['Records']:
       body = json.loads(rec["body"])
       sqs_message = body['Message']
       print(f"s3_message:{sqs_message}")
       if not sqs_message:
           raise ValueError("Invalid event structure")

    #collecting data from S3
    response = s3_client.get_object(Bucket=IN_BUCKET, Key=sqs_message)

    ##read RU data
    ru = RU.RU()
    root_ref = ru.load(response["Body"])
    header = ru.get_header()
    created_time = header['created'].strftime("%Y/%m/%d %H:%M:%S GMT")
    
    ## add connection pool and send message due to SNS trigger to the pool
    htttp = urllib3.PoolManager()

    ## extract messages string variable based on the TSS types
    messagevar = data_extract(root_ref, created_time)
    ## write variable into text
    messagecontent = {"text": messagevar}

    ## post to Slack channel
    slackresp = htttp.request("POST", 
                     SLACK_WEBHOOK_URL,
                     body=json.dumps(messagecontent),
                     headers={"Content-type": "application/json"})

    # TODO implement    
    return {
        'statusCode': 200,
        'body': json.dumps("Message sent successfully.")
    }
