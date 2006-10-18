#!/usr/bin/python
# -*- coding: utf-8 -*-

# Title:	toolbox for szs script
# Date: 	Saturday 6th of November 2004
# Author: 	Norman Köhring
# License:	GPL

from sys import argv
from os import chdir,getenv
from os.path import dirname,abspath
from os.path import exists as fexists
from time import strftime,time
import inspect
chdir(dirname(abspath(argv[0])))



class Error(Exception):
	"""A general Exception which can be used/inherited 
	   from any module""" 
	def __init__(self, reason):
		self.reason = reason
	def __str__(self):
		return repr(self.reason)



class MSG:
	""" all functions to give messages to whatever
	    this class contains: help, debug, say and log """

	
	def ___init___(self):
		""" initializes the variables """

		self.message = ''
		self.place = ''
		self.msgcache = []
		
	
	

	def usage(self, modname = None, modtxt = None):
		""" prints a helpmessage to stdout
		    Usage: msg.usage([modulename [, moduletext ]])
		    Returns: nothing """
		
		print progname+progver
		if modname:
			print "Module:"+ str(modname)
		
		if modtxt:
			print modtxt
		else:
			print """
			Usage:
			./szs.py

			No parameters at the moment.
			For configurations look at szs.cfg,
			for more help look at README.
			"""
	

	
	def debug(self, msg, lvl):
		""" prints debugmessages if lvl >= debuglvl
		    Usage: debug(message, lvl, source)
		    Returns: True and prints the debugmessage """

		if lvl <= debuglevel: # and x == 0:
			src = inspect.getouterframes(inspect.currentframe())[1]
			prefix = ['Critical: ', 'Warning: ', 'Debug: '][lvl-1]
			MSG.log(self, prefix+str(src)+': '+msg)
			print prefix+src[1].split('/')[-1].split('.')[0]+': '+src[3]+'(): '+msg

		return True
#			if cache.get(src) <> None and msg not in cache.get(src)\
#			   or cache.get(src) == None:
#				MSG.log(self, str(src)+": "+msg)
#				print 'Debug from '+str(src)+': '+msg
#
#			if cache.has_key(src):
#				if cache.get(src).has_key(msg):
#					cache.get(src).__setitem__(msg,cache.get(src).get(msg)+1)
#				else:
#					cache.get(src).__setitem__(msg,1)
#			else:
#				cache.__setitem__(src,{msg:1})
#
#			return True
#
#		elif x == 2:
#			MSG.log(self, str(src)+": "+msg)
#			print 'Debug from '+str(src)+': '+msg
#		
#		elif x == 1:
#			MSG.log(self, "...", True)
#			return cache
#		else:
#			return False
	


	def say(self, dict, msg):
		""" dont use it... froze this funtion till next release """

		print "DONT USE THIS FUNCTION (see README for more details)"
		return None 
	


	def log(self, msg, write=False, msgcache=[]):
		""" sends messages to the configured logfile
		    should only be used by 'debug' """

		
		time = strftime('%a%d%b%y %X') 
		if len(msg) > 0 and msg not in msgcache:
			if write:
				F = open(logfile, 'a')		
				F.writelines(msgcache)
				F.close()
			else:
				msgcache.append(time+': '+msg+'\n')
	


class CFG:
	""" functions for reading and writing the config """


	def __init__(self, group):
		
		self.value = ''
		self.group = group

		cfgR = file(cfgF,'r')
		self.cfgL = cfgR.readlines()
		cfgR.close()
	


	def __call__(self, group):

		self.group = group
		return self



	def settings(self):
		""" returns the actual settings
		    Usage: cfg.settings()
		    Returns: ['value','group','cfgF path'] """


		return [self.value, self.group, cfgF.name]
	


	def read(self, value):
		""" reads the configurationfile and returns the values
		    Usage: cfg.read(value)
		    Returns: whats inside value """


		self.value = value
		lst = []

		for part in self.cfgL:
			if part.find('#') < 0:
				if part.split('=')[0] == self.group+'.'+self.value:
					lst.append(part.split('=')[1].strip('\n'))
			elif part.find('#') > 0:
				part = part.split('#')[0]
				if part.split('=')[0] == self.group+'.'+self.value:
					lst.append(part.split('=')[1].strip('\n'))
		if len(lst) > 1:
			return lst
		elif len(lst) == 1:
			return lst[0]
		else:
			return None
	


	def write(self, value):
		""" this function does nothing at the moment
		    in future it writes into the configfiles
		    ...it is maybe planned for third release """


		print "Damn fnords!"
	


class XTRA:
	""" some extra functions like counters """

	def __init__(self):
		""" yeah... the init... """
		
		self.cache = {}


	def countadd(self, y=1, x=[0]):
		""" counter for addition; Usage: xtra.countadd([y [,x ]])
		    where y (standard 1) is the value to add to x
		    Returns: the new value of x """

		x[0] += y
		return x[0]
	


	def countsub(self, y=1, x=[0]):
		""" counter for substraction
		    Usage: xtra.countsub([y ],x ]),
		    where y (standard 1) is the value to substract from x
		    Returns: the new value of x """

		x[0] -= y
		return x[0]



	def strrotate(self, t, l, x=[0]):
		""" trying to build a string rotator
		    Usage: xtra.strrotate(str, length)
		    where 'str' is the String to rotate in
		    'length' units
		    Returns: part of str """

		if x[0] <= len(t):
			x[0] += 1
		else:
			x[0] = 0
		
		ret = [x[0],t[x[0]:x[0]+l]]
		return ret 



	def savevar(self, name, value):
		""" saves variables in the cache, so your module
		    can use it later again...
		    Usage: xtra.savevar(name, value)
		    Returns: Boolean """

		self.cache[name] = value
		if self.cache.has_key(name):
			return True
		else:
			return False
	


	def getvar(self, name):
		""" returns the value of name
		    Usage: xtra.getvar(name)
		    Returns: value of name """

		return self.cache[name]


	
	def delvar(self, name):
		""" deletes the variable from list
		    Usage: xtra.delvar(name)
		    Returns: Boolean """

		del self.cache[name]
		if self.cache.has_key(name):
			return False
		else:
			return True



global cfgF
global logfile
global accuracy
global interval
global debuglevel
global cfgG
global starttime

if fexists(getenv('HOME')+'/.wmi/szs.cfg'):
	cfgF = getenv('HOME')+'/.wmi/szs.cfg'
else:
	cfgF = 'szs.cfg'
cfg = CFG('')
cfgG = cfg('global')		
starttime = time()

logfile = cfgG.read('logfile').strip()
debuglevel = int(cfgG.read('debuglevel').strip())
accuracy = int(cfgG.read('accuracy').strip())
interval = float(cfgG.read('interval').strip())

# determine kernel version
fd = open('/proc/version')
kernel_version = fd.readline()[14:20]
fd.close()

