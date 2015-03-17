#!/usr/bin/python
def bypass(f):
	def nf(*a, **ka):
		return None
	return nf

import syslog

#@bypass
def msg(s):
	syslog.syslog(s)	

def fake(f):
	def nf(*a, **ka):
		msg('Fake invoke: %(command)s'%locals()['ka'])
	return nf


import time

metadata = dict (
	DB_NAME = 'test.db',
	PATH = '/home/ubuntu/odoo_backup/',
	TYPE = ('hourly', 'daily', 'weekly'),
	BACKUP_FILE_PATTERN = '.backup.(?P<backtype>\w+)-(?P<date>.*)',
	BACKUP_COMMAND = 'pg_dump -U odoo -w -h localhost -n public -O ',
	COUNT = 0
)

import os,re
import subprocess as sp

@fake
def issue(command=None):
	if command:
		msg('Execute: '+' '.join(command.split()))
		sp.check_call(command.split())
		
	
def do_backup(t):
	if not t:
		return
	msg(t+' backup begin')
	msg(t+' backup check exsiting backup ... ')
	p = re.compile(metadata['DB_NAME']+metadata['BACKUP_FILE_PATTERN'])
	def check(arg, dirname, names):
		for name in names:
			m = p.match(name)
			if not m:
				continue
			msg('file: '+m.group()+' backuptype: '+m.group('backtype')+' date: '+m.group('date'))
			if m.group('backtype') == t:
				cmd = 'rm '+dirname+m.group()
				issue(command=cmd)

		
	os.path.walk(metadata['PATH'], check, None)
	sig = t+'-'+time.asctime().replace(' ', '-').replace(':', '-')
	cmd = metadata['BACKUP_COMMAND']+metadata['DB_NAME']+' -f '+metadata['PATH']+metadata['DB_NAME']+'.backup.%s'%sig
	issue(command=cmd)
	msg(t+' backup end')



def preodically_backup():
	metadata['COUNT'] += 1
	backup_type = lambda cnt: (cnt%168==0 and 'weekly') or (cnt%24==0 and 'daily') or 'hourly'
	t = backup_type(metadata['COUNT'])
	try:
		do_backup(t)
	except:
		msg('error when doing '+t+' backup!')
	time.sleep(3600) # hourly check

if __name__ == '__main__':
	preodically_backup()

