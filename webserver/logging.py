from flask import current_app
from google.cloud import logging

def get_logger():

	if 'google_cloud_logger' not in current_app.config:
		logging_client = logging.Client()
		current_app.config['google_cloud_logger'] = logging_client.logger('webserver')	

	return current_app.config['google_cloud_logger']


def write_log(severity, msg):
	get_logger().log_text(f'{severity} {msg}')
	print(f'{severity} {msg}')
