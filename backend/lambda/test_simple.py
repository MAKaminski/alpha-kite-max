def lambda_handler(event, context):
    """Simple test Lambda function."""
    return {
        'statusCode': 200,
        'body': 'Hello from Lambda!'
    }
