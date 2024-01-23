'''
logging

Google Cloud Logging is used for service side logs. Google has instructions on how to bind their
logging client to the standard python logging module. Those instructions did not work, so instead
the site is using these simple logging functions.

TODO: bind to std python logging (and be able to set log level on deployment without code changes)
'''
from datetime import datetime
from flask import current_app
from google.cloud import logging
from zoneinfo import ZoneInfo

global_logger = None

def get_logger():
	global global_logger

	if not global_logger:
		logging_client = logging.Client()
		global_logger = logging_client.logger('webserver')

	return global_logger


def write_log(severity, msg):
	time_str = datetime.now(ZoneInfo('US/Pacific')).strftime('%Y-%m-%d %H:%M:%S')
	get_logger().log_text(f'{severity} {msg}')
	print(f'{time_str}: {severity} {msg}')

def print_log(msg):
	time_str = datetime.now(ZoneInfo('US/Pacific')).strftime('%Y-%m-%d %H:%M:%S')
	print(f'{time_str}: {msg}')
