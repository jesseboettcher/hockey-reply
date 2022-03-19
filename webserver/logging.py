from flask import g
from google.cloud import logging

def get_logger():

	if not 'google_cloud_logger' in g:
		logging_client = logging.Client()
		g.google_cloud_logger = logging_client.logger('webserver')	

	return g.google_cloud_logger


def write_log(severity, msg):
	get_logger().log_text(f'{severity} {msg}')
	print(f'{severity} {msg}')
