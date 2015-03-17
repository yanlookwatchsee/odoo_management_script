#!/usr/bin/python

import sys

try:
	dbname,backup_file = sys.argv[1], sys.argv[2]
except:
	print 'Usage: odoo_restore <new_dbname> <backup_file>\n'
	sys.exit(1)

metadata = dict (
	CREATEDB_CMD = 'createdb -U odoo -h localhost %s',
	RESTORE_CMD = 'psql -U odoo -h localhost -d %s -f %s -o restore.log'
)

import subprocess as sp


def fake(f):
	def nf(*a, **ka):
		print('Fake invoke: %(command)s'%locals()['ka'])
	return nf

#@fake
def issue(command=None):
	if command:
		sp.check_call(command.split())

issue(command = metadata['CREATEDB_CMD']%dbname)
issue(command = metadata['RESTORE_CMD']%(dbname, backup_file))


