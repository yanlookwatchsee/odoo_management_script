#!/usr/bin/python
def bypass(f):
	def nf(*a, **ka):
		return None
	return nf

import syslog
import dpsync

#@bypass
def msg(s):
	syslog.syslog(s)	

def fake(f):
	def nf(*a, **ka):
		msg('Fake invoke: %(command)s'%locals()['ka'])
	return nf


import time

metadata = dict (
	PATH = '/home/ubuntu/odoo_backup/',
	TYPE = ('hourly', 'daily', 'weekly'),
	BACKUP_FILE_PATTERN = 'doubletree.db.backup.(?P<backtype>\w+)-(?P<date>.*)',
	BACKUP_COMMAND = 'pg_dump -U odoo -w -h localhost -n public -O doubletree.db -f ',
	COUNT_FILE = '/home/ubuntu/backup.count'
)

import os,re
import subprocess as sp

#@fake
def issue(command=None):
	if command:
		msg('Execute: '+' '.join(command.split()))
		sp.check_call(command.split())
		
	
def do_backup(t):
	if not t:
		return
	c = dpsync.DpClient()
	msg(t+' backup begin')
	msg(t+' backup check exsiting backup ... ')
	p = re.compile(metadata['BACKUP_FILE_PATTERN'])
	def check(arg, dirname, names):
		for name in names:
			m = p.match(name)
			if not m:
				continue
			msg('file: '+m.group()+' backuptype: '+m.group('backtype')+' date: '+m.group('date'))
			if m.group('backtype') == t:
				cmd = 'rm '+dirname+m.group()
				issue(command=cmd)
				try:
					c.delete(name)
					msg('Dropbox file deleted')
				except:
					msg('No such file: %s'%name)
				
		
	os.path.walk(metadata['PATH'], check, None)
	sig = t+'-'+time.asctime().replace(' ', '-').replace(':', '-')
	cmd = metadata['BACKUP_COMMAND']+metadata['PATH']+'doubletree.db.backup.%s'%sig
	issue(command=cmd)
	msg('pg_dump done')
	try:
		c.put(metadata['PATH']+'doubletree.db.backup.%s'%sig)
		msg('Upload to dropbox')
	except:
		msg('Dropbox sync error!')
	msg(t+' backup end')

def increase_count():
	cnt_file = metadata['COUNT_FILE']
	cnt = 0
	try:
		with open(cnt_file, 'r') as f:
			cnt = int(f.read())
	except IOError:
		msg(cnt_file+' not found!')
		with open(cnt_file, 'w') as f:
			f.write('0')
	cnt+=1
	with open(cnt_file, 'w') as f:
		f.write(str(cnt))
	return cnt

def preodically_backup():
	backup_count = increase_count()
	backup_type = lambda cnt: (cnt%168==0 and 'weekly') or (cnt%24==0 and 'daily') or 'hourly'
	t = backup_type(backup_count)
	try:
		do_backup(t)
	except:
		msg('error when doing '+t+' backup!')

if __name__ == '__main__':
	preodically_backup()

