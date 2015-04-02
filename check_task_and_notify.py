#!/usr/bin/python

import smtplib
import time, syslog
import psycopg2 as pg


G_SETTINGS = None

def msg(s):
	syslog.syslog(s)


def debug_filter(f):
	def nf():
		return [ e for e in f() if e[2]==G_SETTINGS['DEVELOPER_NAME']]
	return nf



def load_settings():
	d=dict()
	with open('/etc/odoo/.pass', 'r') as p:
		for line in p:
			l= [ s.strip() for s in line.split(':') ]
			d[l[0]]=l[1]
	return d
		

@debug_filter
def fetch_task():
	FETCHCMD = """
select c.name,c.login1,c.username1, d.login as login2, d.name as username2,c.date_deadline from 
(
select a.name,b.login as login1, b.name as username1,a.date_deadline, a.reviewer_id from 
	(select name,user_id,reviewer_id, date_deadline from project_task where date_deadline is  not NULL   and kanban_state='normal') as a
	join 
	(select x.id, x.login, y.name from res_users as x join res_partner as y on x.partner_id=y.id) as b 
	on a.user_id=b.id
) as c
join 
( 
   select xx.id, xx.login, yy.name from res_users as xx join res_partner as yy on xx.partner_id=yy.id
) as d 
on c.reviewer_id=d.id;
"""
	try:
		conn=pg.connect("dbname='"+G_SETTINGS['ODOO_DB_NAME'] \
						+ "' user='"+G_SETTINGS['ODOO_ACCOUNT'] \
						+ "' password='"+G_SETTINGS['ODOO_PASSWORD'] \
						+"' host='"+G_SETTINGS['ODOO_DB_HOST']+"'")
		c = conn.cursor()
		c.execute(FETCHCMD)
		ret = c.fetchall()
	finally:
		conn.close()
	return ret


class NotifyAgent:
	def uniq(self, l):
		s=set()
		return filter (lambda x: x not in s and not s.add(x), l)

	def get_date_delta(self, year, month, day):
		now = time.time()
		due = time.mktime( (year,month,day,0,0,0,0,0,0) )
		return int((due-now+24*3600-1)/(24*3600))
		
	def notify(self, dst, task, due_date, cond=None): 
		#to be implemented by concrete instance
		pass

	def close(self):
		#to be implemented by concrete instance
		pass

	def compose_msg(self, dst, task, due_date): 
		l, t = [], [x[1] for x in dst]
		for i,e in enumerate(t):
			if e not in t[i+1:]:
				l.append(e)

		towhom = len(l)>1 and (' '.join(l[:-1]))+' and '+l[-1]  or l[0]

		delta = 0
		if due_date: delta = self.get_date_delta(due_date[0], due_date[1], due_date[2])
		timedetail = "%d day %s"%(abs(delta), delta>=0 and 'before' or 'after')
		return 	"""
Hi %s,

	Your task *** %s *** is %s the deadline date. 
	
	Please resolve this issue by either
	1) postpone the deadline date on task panel or 
	2) if you've already finished the task, mark it as \"Finished\" or 
	3) if the task is blocked, mark it as \"Blocked\".

	Note that you will not stop receiving this mail alert unless you resolve this due task issue.
	
	Thanks,
	%s
				
				""" %(towhom, task, timedetail, G_SETTINGS['NA_SIGNATURE'])
	
class MailNotifyAgent(NotifyAgent):
	def __init__(self):
		self.ACCOUNT = G_SETTINGS['GMAIL_ACCOUNT']
		self.PASSWORD = G_SETTINGS['GMAIL_PASSWORD']
		self.server = smtplib.SMTP_SSL(G_SETTINGS['GMAIL_GATEWAY'])
		#self.server.set_debuglevel(1)
		self.server.login(self.ACCOUNT, self.PASSWORD)

	def notify(self, dst, task, due_date, cond=None):
		delta = self.get_date_delta(due_date[0], due_date[1], due_date[2])
		if delta >1: return
		fromaddr = self.ACCOUNT
		toaddrs  = self.uniq([x[0] for x in dst])
		header = "From: \"%s\" <%s>\r\nTo: %s\r\n" \
						% (G_SETTINGS['NA_DISPLAY_NAME'], fromaddr, ", ".join(toaddrs))\
						 + "Subject: Alert of Task \"%s\"\r\n\r\n"%task
		msg('Ready to send mail alert:\n'+header)
		self.server.sendmail(fromaddr, toaddrs, header+self.compose_msg(dst,task,due_date))
		msg('Mail alert done!')
	
	def close(self):
		self.server.quit()


class STDINNotifyAgent(NotifyAgent):
	def notify(self, dst, task, due_date, cond=None):
		delta = self.get_date_delta(due_date[0], due_date[1], due_date[2])
		msg( '****** %d'%delta)
		if delta >1: return
		msg(self.compose_msg(dst, task, due_date))
		
def get_notify_agent(t="STDIN"):
	if t=='STDIN':
		return STDINNotifyAgent()
	elif t=='MAIL':
		return MailNotifyAgent()

	
G_SETTINGS = load_settings()

na=get_notify_agent('MAIL')
#na=get_notify_agent()
tasks = fetch_task()

for task in tasks:
	d = task[5]
	msg('Ready to notify!\n')
	na.notify([ (task[1], task[2]) ,(task[3], task[4]) ], task[0], (d.year, d.month, d.day))
	msg('Notify done!\n')

na.close()


