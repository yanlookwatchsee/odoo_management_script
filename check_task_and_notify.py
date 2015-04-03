#!/usr/bin/python

import smtplib
import time, syslog
import psycopg2 as pg


G_SETTINGS = None

def tee_to_stdout(f):
	def nf(s):
		print s
		f(s)
	return  nf
	

#@tee_to_stdout
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
		


def retrive_project_info(project_id):
	msg("project_id=%s"%str(project_id))
	RETRIVECMD = """
select xx.project_id, xx.name, xx.cpo, xx.partner_id, yy.name
from
(select x.project_id, x.name,y.client_order_ref as cpo, x.partner_id 
from
(select a.id as project_id, b.id as analytic_id, b.name, b.partner_id as partner_id from project_project as a join account_analytic_account as b on a.analytic_account_id=b.id) as x
left join 
sale_order as y
on y.project_id =x.analytic_id) as xx
left join
res_partner as yy
on xx.partner_id=yy.id 
where xx.project_id = %s
""" % str(project_id)

	try:
		conn=pg.connect("dbname='"+G_SETTINGS['ODOO_DB_NAME'] \
						+ "' user='"+G_SETTINGS['ODOO_ACCOUNT'] \
						+ "' password='"+G_SETTINGS['ODOO_PASSWORD'] \
						+"' host='"+G_SETTINGS['ODOO_DB_HOST']+"'")
		c = conn.cursor()
		c.execute(RETRIVECMD)
		ret = c.fetchall()
	finally:
		conn.close()
	if len(ret):
		return (ret[0][0], ret[0][1], ret[0][4], [x[2] for x in ret if x[2]])
	return None


#@debug_filter
def fetch_task():
	FETCHCMD = """
select c.name,c.login1,c.username1, d.login as login2, d.name as username2,c.date_deadline, c.project_id from 
(
select a.name,b.login as login1, b.name as username1,a.date_deadline, a.reviewer_id, a.project_id from 
	(select name,user_id,reviewer_id, date_deadline, project_id from project_task where date_deadline is  not NULL   and kanban_state='normal') as a
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
		
	def notify(self, dst, task, due_date, project_id=None, cond=None): 
		#to be implemented by concrete instance
		pass

	def close(self):
		#to be implemented by concrete instance
		pass

	def compose_msg(self, dst, task, due_date, project_id=None): 
		l, t = [], [x[1] for x in dst]
		for i,e in enumerate(t):
			if e not in t[i+1:]:
				l.append(e)

		towhom = len(l)>1 and (' '.join(l[:-1]))+' and '+l[-1]  or l[0]

		delta = 0
		if due_date: delta = self.get_date_delta(due_date[0], due_date[1], due_date[2])
		timedetail = "%d day %s"%(abs(delta), delta>=0 and 'before' or 'after')
		fromaddr = G_SETTINGS['GMAIL_ACCOUNT']

		toaddrs  = self.uniq([x[0] for x in dst])
		compose_d =dict( WHO=towhom, TASK=task, DELTA=timedetail,\
						 SIGNATURE=G_SETTINGS['NA_SIGNATURE'], PROJECT=None,\
						 CUSTOMER=None, CUS_PO=None)

		ret = retrive_project_info(project_id);
		if len(ret):
			compose_d.update(dict(PROJECT=ret[1], CUSTOMER=ret[2], CUS_PO=', '.join(ret[3])))
		subject = "Subject: Alert of Task \"%(TASK)s\" of Project \"%(PROJECT)s\" for Customer \"%(CUSTOMER)s\"\r\n\r\n"%compose_d
		header = "From: \"%s\" <%s>\r\nTo: %s\r\n" \
						% (G_SETTINGS['NA_DISPLAY_NAME'], fromaddr, ", ".join(toaddrs))\
						 + subject

		
		body = """
Hi %(WHO)s,

	Your task *** %(TASK)s *** is %(DELTA)s the deadline date. 
	
	Please resolve this issue by either within the ERP system:
	1) postpone the deadline date on task panel or 
	2) if you've already finished the task, mark it as \"Finished\" or \"blocked\"  per the instruction below.

	!!! Note that you will continually receiving this email alert every day UNTIL  you resolve this due task issue.
	
	Project and order infomation:
	
	Task            : %(TASK)s
	Project         : %(PROJECT)s
	Customer        : %(CUSTOMER)s
	Customer PO#    : %(CUS_PO)s


	Thanks,
	%(SIGNATURE)s

	-------------------------------------------------------------
	Instructions to resolve this issue on ERP:
	
	Step 1: Login to ERP and go to to \"Project\" -> \"Task\" page.
	Step 2: Edit the task and either a) delete the deadline_date, 
			b) postpone the deadline_date 
			c) toggle the small circle on the up right corner to mark this task as \"Ready to next stage\" or "Blocked",
			d) delete deadline date of task.
	
	
				
				""" %compose_d

		return header+body	

class MailNotifyAgent(NotifyAgent):
	def __init__(self):
		self.ACCOUNT = G_SETTINGS['GMAIL_ACCOUNT']
		self.PASSWORD = G_SETTINGS['GMAIL_PASSWORD']
		self.server = smtplib.SMTP_SSL(G_SETTINGS['GMAIL_GATEWAY'])
		#self.server.set_debuglevel(1)
		self.server.login(self.ACCOUNT, self.PASSWORD)

	def notify(self, dst, task, due_date, project_id=None, cond=None):
		delta = self.get_date_delta(due_date[0], due_date[1], due_date[2])
		if delta >1: return
		
		
		fromaddr = G_SETTINGS['GMAIL_ACCOUNT']
		toaddrs  = self.uniq([x[0] for x in dst])
		msg('Ready to send mail alert:\n')
		message = self.compose_msg(dst,task,due_date, project_id)
		msg(message)
		self.server.sendmail(fromaddr, toaddrs, message)
		msg('Mail alert done!')
	
	def close(self):
		self.server.quit()


class STDINNotifyAgent(NotifyAgent):
	def notify(self, dst, task, due_date,project_id=None,  cond=None):
		delta = self.get_date_delta(due_date[0], due_date[1], due_date[2])
		msg( '****** %d'%delta)
		if delta >1: return
		if project_id: msg(str(retrive_project_info(project_id)))
		msg(self.compose_msg(dst, task, due_date, project_id))
		
def get_notify_agent(t="STDIN"):
	if t=='STDIN':
		return STDINNotifyAgent()
	elif t=='MAIL':
		return MailNotifyAgent()

	
G_SETTINGS = load_settings()

na=get_notify_agent('MAIL')
tasks = fetch_task()
msg('Begin Check # of Task is %d\n'%len(tasks) )
for task in tasks:
	d = task[5]
	na.notify([ (task[1], task[2]) ,(task[3], task[4]) ], \
				task[0], (d.year, d.month, d.day), task[6])

na.close()


