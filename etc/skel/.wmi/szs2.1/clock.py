#!/usr/bin/python

# module that shows a clock
#
# TODO
#
# * finish support for 'workbeat'


from time import strftime,time,localtime,mktime
import szstoolbox

ready = False

def init():
	""" the init thingy """
	
	global frmt, ready, acc, lst, bar
	global wbdir, wbshow, wbstart, wbstop, wblabel, ew, sw, wboutside
	bar = None
	msg = szstoolbox.MSG()
	cfg = szstoolbox.CFG('clock')
	workbeat = cfg.read('workbeat')
	if len(workbeat) > 0:
		wbdir = cfg.read('wbdirection')
		wboutside = cfg.read('wboutside')
		if wboutside not in ('yes','no'):
			wboutside = 'yes'
			msg.debug('illegal value for wboutside, using "yes"',2)
		wbshow = cfg.read('wbshow')
		if wbshow in ('bar','meter','both'):
			wblabel = cfg.read('wblabel')
		if wbshow in ('text','both'):
			ew = int(cfg.read('ew')) # EndWith
			sw = int(cfg.read('sw')) # StartWith		
	else:
		wbdir == None
		wbshow == None
	acc = int(szstoolbox.CFG('global').read('accuracy'))
	frmt = str(cfg.read('format')).strip()
	lst = frmt.split('%N')
	ready = True

	if wbdir not in ('up','down',None):
		wbdir = 'up'
		msg.debug('illegal workbeat direction, using "up"',2)
	
	if wbshow not in ('bar','meter','text','both',None):
		wbshow = 'both'
		msg.debug('illegal workbeat show option, using "both"',2)

	if wbshow and wbdir:
		workbeat = workbeat.split(',')
		wbstart = workbeat[0].split(':')
		wbstop = workbeat[1].split(':')
def main():
	""" the main function """

	global frmt,workbeat,bar
	if not ready:
		init()
		return ['init']

	if len(lst) > 1:
		y = '@'+str(round((((time()+3600)%86400)/86.4),acc))
		y = y[:y.find('.')+acc+1]
		while len(y[y.find('.')+1:len(y)]) < acc: y=y+'0'
		frmt = lst[0]+y+lst[1]
	
	if wbshow <> None and wbdir <> None:
		tpl1 = list(localtime())
		tpl2 = list(localtime())
		tpl1[3] = int(wbstart[0])
		tpl1[4] = int(wbstart[1])
		tpl2[3] = int(wbstop[0])
		tpl2[4] = int(wbstop[1])
		start = mktime(tuple(tpl1))
		stop = mktime(tuple(tpl2))
		spanne = stop-start
		jetzt = time() - start
		
#		### DEBUGSECTION ###
#		print '--------D-E-B-U-G--------'
#		print 'Start: '+str(start)#starttime
#		print 'Stop: '+str(stop) #endtime
#		print 'Spanne: '+str(spanne) #stop-start
#		print 'Jetzt: '+str(jetzt) #now
#		print 'wbshow: '+wbshow #showtype
#		print 'wbdir: '+wbdir #direction
#		print str(int(round(jetzt*100/spanne)))+'%'+wblabel #bar
#		print str(100-int(round(jetzt*100/spanne)))+'%'+wblabel #100-bar
#		print '--------D-E-B-U-G--------'
#		### END OF DEBUG ###

		wb = jetzt * 100 / spanne
		wb = int(round(wb))
		if wboutside == 'yes':
			if wb > ew:
				wb = ew
			elif wb < sw:
				wb = sw
		else:
			if wb > ew or wb < sw:
				wb = None

		tmp = frmt

		if wb <> None:
			if wbdir == 'down':
				wb = 100 - wb		
			if wbshow in ('bar','meter'):
				wbthing = None
				if wb >= 0:
					bar = str(wb)+'%'+wblabel
				else:
					bar = '0%'+wblabel
			elif wbshow == 'text':
				tmp = frmt+' ('+str(wb)+'%%)'
				bar = None
			else:
				tmp = frmt+' ('+str(wb)+'%%)'
				if wb >= 0:
					bar = str(wb)+'%'+wblabel
				else:
					bar = '0%'+wblabel
		else:
			bar = None
			
	if bar <> None:
		return [strftime(tmp),bar]
	else:
		return [strftime(tmp)]

def debug():
	print "============================="
	print "frmt type is "+str(type(frmt))+" (should be 'str')"
	print "bar type is "+str(type(bar))+" (should be 'str' or 'NoneType')"
	print "outputted text: '"+strftime(frmt)+"'"
	print "outputted bar: '"+str(bar)+"'"
	print "Netbeat should be: @"+str(round((((time()+3600)%86400)/86.4),acc))
	print "Actual time should be: "+strftime("%X")
	print "Actual date should be: "+strftime("%x")
	print "============================="
	
if __name__ == '__main__':
	""" only to debug... """

	from sys import argv
	from time import sleep

	if "loop" in argv:
		while 1 == 1:
			main()
			debug()
			sleep(1)
	else:
		main()
		debug()

