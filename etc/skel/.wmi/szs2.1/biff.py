#!/usr/bin/python
"""
szs/biff - an imap/pop biff module for SZS a statusbar script for WMI


CHANGELOG:

   v0.4    2004-12-14
   		* changed config format
		* added multiple server support
		* added pop3 support
		* added seperate multipliers for pop and imap
		* added support for POP3 SSL (python 2.4 only)
		* added support for IMAP4 SSL 

   v0.3    2004-11-29  
   		* show <mailbox>(?) on startup and if serer is not reachable

   v0.2    2004-11-26  
   		* implemented error handling
		* some cleanups

   v0.1    2004-11-25  
        * initial Release


TODO:



COPYRIGHT:

Copyright 2004  Christoph Wegscheider <cw@wegi.net>


LICENSE:

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 2 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
"""


import imaplib
import poplib
import socket
import types
import sys
import szstoolbox



def error(mailboxes):
	text = ''
	if type(mailboxes) is not types.ListType:
		mailboxes = [['', mailboxes]]
	for it in mailboxes:
		text += it[1] + '(?) '
	return text



def main():
	global count
	global imaptext
	global poptext

	# check imap server	
	if count % multiplier['imapmultiplier'] == 1:
		imaptext = ''
		for acc in accounts['imapaccount']:
			try:
				if acc[3] == 'yes':
					server = imaplib.IMAP4_SSL(acc[0])
				else:
					server = imaplib.IMAP4(acc[0])
				server.login(acc[1], acc[2])
				for it in acc[4:]:	
					if server.select(it[0], True)[0] == 'OK':
						num = len(server.search(None, 'UNSEEN')[1][0].split())
						if num > 0:
							imaptext += it[1] + '(' + str(num) + ') '
				server.logout()
			except (imaplib.IMAP4.error, socket.error), errormsg:
				msg.debug(acc[0] + ": " + str(errormsg), 2)
				imaptext += error(acc[4:])

	# check pop3 server
	if count % multiplier['popmultiplier'] == 1:
		poptext = ''
		for acc in accounts['popaccount']:
			try:
				if acc[3] == 'yes':
					if sys.version_info >= (2,4):
						server = poplib.POP3_SSL(acc[0])
					else:
						raise szstoolbox.Error('POP3 with SSL support is only availabe in python 2.4 or greater')
				else:
					server = poplib.POP3(acc[0])
				server.user(acc[1])
				server.pass_(acc[2])
				num = server.stat()[0]
				server.quit()
				if num > 0:
					poptext += acc[4] + '(' + str(num) + ') '
			except (poplib.error_proto, socket.error, szstoolbox.Error), e:
				msg.debug(acc[0] + ': ' + str(e), 2)
				poptext += error(acc[4])
			
	count += 1
	return [imaptext + poptext]



# init
count = 0
imaptext = poptext = ''
accounts = multiplier = {}
msg = szstoolbox.MSG()
cfg = szstoolbox.CFG('biff')

# load configuration  
for it in 'imapmultiplier','popmultiplier':
	multiplier[it] = int(cfg.read(it))
for acctype in 'imapaccount','popaccount':
	accounts[acctype] = []
	config = cfg.read(acctype)
	if type(config) is types.StringType:
		config = [config]
	elif type(config) is types.NoneType:
		config = []
	for acc in config:
		acc = acc.split(',')
		accounts[acctype].append(acc[0].split(':'))
		if acctype == 'imapaccount':
			accounts[acctype][-1].extend([it.split(':') for it in acc[1:]])

# set nice start text
for acc in accounts['imapaccount']:
	imaptext += error(acc[3:])
for acc in accounts['popaccount']:
	poptext += error(acc[4])



# for testing purpose
if __name__ == '__main__':
	import time

	while True:
		print main()
		time.sleep(szstoolbox.interval)
