#!/usr/bin/python

import sys

try:
	dbname,backup_file = sys.argv[1], sys.argv[2]
except:
	print 'Usage: odoo_restore <new_dbname> <backup_file>\n'
	sys.exit(1)

metadata = dict (
	CREATEDB_CMD = 'createdb -U %(ODOO_ACCOUNT)s -h %(ODOO_DB_HOST)s %(NEW_DB_NAME)s',
	RESTORE_CMD = 'psql -U %(ODOO_ACCOUNT)s -h %(ODOO_DB_HOST)s -d %(NEW_DB_NAME)s -f %(BACKUP_FILE)s -o restore.log'
)

import subprocess as sp


G_SETTINGS = None

def load_settings():
	d=dict()
	with open('/etc/odoo/.pass', 'r') as p:
		for line in p:
			l= [ s.strip() for s in line.split(':') ]
			d[l[0]]=l[1]
	return d

def fake(f):
	def nf(*a, **ka):
		print('Fake invoke: %(command)s'%locals()['ka'])
	return nf

@fake
def issue(command=None):
	if command:
		sp.check_call(command.split())

if __name__ == '__main__':
	G_SETTINGS = load_settings()
	G_SETTINGS['NEW_DB_NAME'] = dbname
	G_SETTINGS['BACKUP_FILE'] = backup_file
	issue(command = metadata['CREATEDB_CMD']%G_SETTINGS)
	issue(command = metadata['RESTORE_CMD']%G_SETTINGS)


