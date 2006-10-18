#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
COPYRIGHT:

Copyright 2004  Norman Köhring <nkoehring-at-web-dot-de>


LICENSE:

This program and all of its modules are free software;
you can redistribute it and/or modify it under the terms of the
GNU General Public License as published by the Free Software Foundation;
either version 2 of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA

For more information read the file LICENSE
"""


import sys, szstoolbox
from commands import getstatusoutput
from time import strftime,sleep,time
from os.path import exists as fexists
		

# initial variables
progname = 'Python SZS '
progver = '1st'

class moduleclass:
	""" class for importing the modules and get there outputs
	    Usage: It should be enough to create an instance... """

	def __init__(self):
		""" initialize all the things in modules """

		x = str(cfgM.read('modules')).strip().split(',')
		self.mods=[]
		msg.debug('Module: %s' % str(x), 3)
		for mod in x:
			try:
				self.mods.append(__import__(mod, globals(), locals(), []))
			except ImportError:
				msg.debug("Can't find %s. Maybe you dispelled it?" % mod, 2)

			except ValueError:
				msg.debug("No modules to load.", 2)
				x = []

			except:
				raise



	def txtsnbars(self):
		x = []
		y = []
#		lst = []
		for mod in self.mods:
			try:
				lst = mod.main()
				lst[0] = lst[0].strip()
				if lst[0] != '':
					x.append(lst[0])
				
				y.extend(lst[1:])
					
			except:
				raise
		
		return [x,y]



class init:
	""" this class contains all function for the script initialization """

	def __init__(self):
		""" yes, also init needs an init! """

		init.classes(self)
		init.args(self)
		init.vars(self)



	def classes(self):
		""" initialize the classes """

		global cfg
		global cfgG
		global cfgM
		global msg
		global modules
		global xtra
		msg = szstoolbox.MSG()
		cfg = szstoolbox.CFG('')
		cfgM = cfg('main')
		modules = moduleclass()
		xtra = szstoolbox.XTRA()



	def args(self):
		""" initializes the arguments """

		if len(sys.argv) >= 2:
			if sys.argv[1] in ('-?','-h','--help'):
				msg.usage()
				sys.exit(0)
			else:
				print 'No parameters, sorry...'
				print '-?, -h or --help for help'
				sys.exit(0)
	


	def vars(self):
		""" sets the variables """

		global welcome
		global text
		global prog		
		global seperator		
		welcome = cfgM.read('welcome').strip()
		prog = [str(cfgM.read('prog_txt')).strip(),str(cfgM.read('prog_bar')).strip()]
		if not fexists(prog[0].split(' ')[0]):
			msg.debug(str(prog[0])+' doesn\'t not exists, switched it to `echo `',2)
			prog[0] = 'echo '
		else:
			msg.debug('Using '+str(prog[0])+' to display text',3)

		if not fexists(prog[1].split(' ')[0]):
			msg.debug(str(prog[1])+' doesn\'t not exists, switched it to `echo `',2)
			prog[1] = 'echo '
		else:
			msg.debug('Using \''+str(prog[1])+'\' to display bars',3)

		seperator = cfg('global').read('seperator')



def main():
	""" the main function: nothing special. it only runs the commands and maybe return the errors """
	
	if 'welcome' in globals() and welcome <> '!NONE':
		if time() - szstoolbox.starttime <= 3:
			now = welcome
		else:
			now = ''

	txtsnbars = modules.txtsnbars()

#	for i,j in txtsnbars:
	txts = seperator.join(txtsnbars[0]).strip()
	bars = ','.join(txtsnbars[1]).strip(',')
	
	cmdtxt = str(prog[0]+' \''+now+' '+txts+'\'')
	cmdbar = str(prog[1]+' \''+bars+'\'')

	error = getstatusoutput(cmdtxt)
	if error[0] == 0: 
		error = getstatusoutput(cmdbar)
	return error



if __name__ == "__main__":
	init()
	error_nr = 0
	error_msg = 'noerror'
	while error_nr == 0:
		try:
			error = main()
			error_nr = error[0]
			error_msg = error[1]
			sleep(szstoolbox.interval)
		except KeyboardInterrupt:
			sys.exit('goodbye')
		except:
			raise
			sys.exit("Terminated cause above error(s)") # eigentlich ist diese Zeile hirnlos :-S


	print 'Error...'
#	print 'Nr: '+str(error_nr)+' Msg:'+error_msg
	print str(error)
	sys.exit('error')
