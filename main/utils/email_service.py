import boto3
from decouple import config
from botocore.exceptions import BotoCoreError, ClientError


def get_ses_client():
    """
    Creates and returns a configured boto3 SES client.
    Requires AWS credentials and region in environment variables.
    """
    return boto3.client(
        "ses",
        aws_access_key_id=config("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=config("AWS_SECRET_ACCESS_KEY"),
        region_name=config("AWS_REGION_NAME", "us-east-1"),
    )


def send_email(subject, body_text, body_html=None, recipient=None):
    """
    Sends an email via AWS SES.
    Supports both plain text and HTML body formats.

    Args:
        subject (str): Email subject line.
        body_text (str): Fallback plain-text message body.
        body_html (str, optional): HTML version of the email body.
        recipient (str, optional): Recipient email address.
            Defaults to SES_RECEIVER from environment variables.
    Returns:
        bool: True if sent successfully, False otherwise.
    """
    ses = get_ses_client()
    sender = config("SES_SENDER")
    recipient = recipient or config("SES_RECEIVER")

    if not sender or not recipient:
        print("❌ Missing SES_SENDER or recipient address.")
        return False

    # Build email body
    body = {"Text": {"Data": body_text, "Charset": "UTF-8"}}
    if body_html:
        body["Html"] = {"Data": body_html, "Charset": "UTF-8"}

    try:
        response = ses.send_email(
            Source=sender,
            Destination={"ToAddresses": [recipient]},
            Message={
                "Subject": {"Data": subject, "Charset": "UTF-8"},
                "Body": body,
            },
        )
        message_id = response["MessageId"]
        print(f"✅ Email sent successfully! Message ID: {message_id}")
        return True
    except (BotoCoreError, ClientError) as e:
        print("❌ SES Error:", str(e))
        return False
