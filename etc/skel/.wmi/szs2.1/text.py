#!/usr/bin/python

# module to show specific text static or as marquee

from szstoolbox import CFG,XTRA

def init():
	cfg = CFG('text')
	xtra = XTRA()
	global xtra,txt,bar,marq,l
	txt = str(cfg.read('txt')).strip()
	bar = str(cfg.read('bar')).strip()
	marq = int(cfg.read('marquee'))
	if marq == 1:
		l = int(cfg.read('length'))
	else:
		l = None

def main():
	ret = ['','']
	if not 'txt' in globals():
		init()
	else:
		if marq == 1:
			ret[0] = xtra.strrotate(txt,l)[1]
		else:
			ret[0] = txt

		if len(bar) > 0:
			ret[1] = bar
		else:
			ret[1] = '' 

		return ret

	return ret
