#!/usr/bin/python
import subprocess as sp
import os
from dropbox import client, rest, session

class DpClient:
	def login(self):
		self.app_key = '4r474afwyk3z6q2'
		self.app_secret = 'mq7ttcmg3pkxv5c'
		self.flow = client.DropboxOAuth2FlowNoRedirect(self.app_key, self.app_secret)
		authorize_url = self.flow.start()
		print "1. Go to: " + authorize_url
		print "2. Click \"Allow\" (you might have to log in first)."
		print "3. Copy the authorization code."
		code = raw_input("Enter the authorization code here: ").strip()
		access_token, user_id = self.flow.finish(code)
		with open(self.TOKEN_FILE, 'w') as f:
			f.write(access_token)

	def __init__(self):
		self.TOKEN_FILE = 'token_file'
		try:
			with open(self.TOKEN_FILE, 'r') as f:
				access_token = f.read()
				self.api_client = client.DropboxClient(access_token)
		except:
			self.login()

	def put(self, path):
			with open(path, 'rb') as from_file:
				self.api_client.put_file(path.split('/')[-1], from_file)

	def delete(self, path):
			self.api_client.file_delete(path)




