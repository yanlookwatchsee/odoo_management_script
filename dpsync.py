#!/usr/bin/python
import subprocess as sp
import os
from dropbox import client, rest, session

class DpClient:
	def login(self):
		self.DP_PASS_FILE = '/home/ubuntu/.dropboxpass'
		with open(self.DP_PASS_FILE) as f:
			l = f.read().split()
			self.app_key, self.app_secret = l[0], l[1]

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
		self.TOKEN_FILE = '/etc/odoo/.dp_token_file'
		try:
			with open(self.TOKEN_FILE, 'r') as f:
				access_token = f.read().strip()
				self.api_client = client.DropboxClient(access_token)
		except:
			raise
			self.login()

	def put(self, path):
			with open(path, 'rb') as from_file:
				self.api_client.put_file(path.split('/')[-1], from_file)

	def delete(self, path):
			self.api_client.file_delete(path)



if __name__ == '__main__':
	c = DpClient()

