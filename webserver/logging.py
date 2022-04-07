from flask import current_app
from google.cloud import logging

global_logger = None

def get_logger():
	global global_logger

	if not global_logger:
		logging_client = logging.Client()
		global_logger = logging_client.logger('webserver')

	return global_logger


def write_log(severity, msg):
	get_logger().log_text(f'{severity} {msg}')
	print(f'{severity} {msg}')
