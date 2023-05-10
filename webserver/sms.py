from dotenv import load_dotenv
from flask import Flask, request
import os
import threading
from twilio.rest import Client

# Load environment variables from .env file
load_dotenv('keys/.env')

ENABLE_SMS = True

class SMS:
    def __init__(self):
        self.client = Client(os.getenv("TWILIO_ACCOUNT_ID"), os.getenv("TWILIO_TOKEN"))
        self.twilio_phone_number = os.getenv("TWILIO_PHONE_NUMBER")

    def send(self, recipients, message):

        if not ENABLE_SMS:
            return

        for recipient in recipients:
            self.client.messages.create(
                body=message,
                from_=self.twilio_phone_number,
                to=recipient
            )
