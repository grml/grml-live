import szstoolbox

ready = False
def init():
	""" globalizes and initializes the variables """
	global ready
	ready = False

	global batanimload, batstateF
	global lpart1, lpart2, l
	global msg, xtra, cfg
	global lastfull, acc, lvar, tvar, batlabel,state
	state = ''
	
	msg = szstoolbox.MSG()
	xtra = szstoolbox.XTRA()
	cfg = szstoolbox.CFG('battery')
	cfgG = szstoolbox.CFG('global')

	batstateF = cfg.read('batstate').strip()
	batinfoF = cfg.read('batinfo').strip()
	batanimload = int(cfg.read('animbatload').strip())
	batlabel = cfg.read('label').strip()
	lvar = int(cfg.read('lvar').strip())
	tvar = int(cfg.read('tvar').strip())
	acc = int(cfgG.read('accuracy').strip())
	batstateF = open(batstateF,'r')
	batinfoF = open(batinfoF,'r')
	state = None

	infoLn = batinfoF.readlines()
	for line in infoLn:
		line = line.split(':')
		part1 = line[0].strip()
		part2 = line[1].strip()
		if part1 == 'last full capacity':
			lastfull = part2[:part2.find(' ')]

	ready = True



def main():
	""" main function... returns a list with a string like
	    "/65\" or "\BAT LOW/" and an integer like 65 that
	    shows procentual state of your battery """

	global state

	if not ready:
		init()
		return ['init','']

	if batanimload > 0:
		z = xtra.countadd(5)
		if z >= 95:
			z = 0
	else:
		z = 0

	stateLn = batstateF.readlines()
	batstateF.seek(0)
	remain = '0'

	for line in stateLn:
		line = line.split(':')
		part1 = line[0].strip()
		part2 = line[1].strip()
		if part1 == 'present' and part2 == 'no':
			msg.debug('Battery not present',2)
			state = None
			return ['']
		elif part1 == 'charging state' and part2 == 'discharging':
			if state <> '-':
				msg.debug('Battery is discharging',3)
				state = '-'
		elif part1 == 'charging state' and part2 == 'charging':
			if state <> '+':
				msg.debug('Battery is charging',3)
				state = '+'
		elif part1 == 'charging state' and part2 == 'unknown':
			if state <> '#':
				msg.debug('Battery seems full (charging state is unknown)',3)
				state = '#'
		elif part1 == 'remaining capacity':
			remainold = part2
			remain = part2[:part2.find(' ')]
			remain = float(remain)*100/float(lastfull)
			remain = str(round(remain,acc))
			remain = remain[:remain.find('.')+3]+'%'
	
	if lvar in (1,2,3):
		if state == '#':
			ls = ' (full)'
		else:
			if lvar == 2:
				ls = ' ('+remainold+str(state)+')'
			if lvar == 3:
				ls = ' ('+remainold+'/'+remain+')'
			else:
				ls = ' ('+remain+str(state)+')'
	else:
		ls = ''
		
	if tvar in (1,2,3):
		if state == '#':
			ts = ''
		else:
			if tvar == 2:
				ts = remainold
			if tvar == 3:
				ts = remainold+'|'+remain
			else:
				ts = remain
	else:
		ts = ''
		
	if batanimload > 0:
		bar = '!'+remain+'%'+batlabel+ls
	else:
		bar = '!'+z+'%'+batlabel+ls
	
	if state == '+' and tvar >= 0:
		return ['/'+ts+'\\',bar]
	elif state == '-' and tvar >= 0:
		return ['\\'+ts+'/',bar]
	elif state == '#' or tvar < 0:
		return ['',bar]
	elif state == None:
		return ['']
	else:
		print 'Undefined state: "'+str(state)+'"'
		return ['???','???']
	


if __name__ == '__main__':
        """ helps to debug the script """

        from sys import argv
        from time import sleep


        if 'loop' in argv:
                while '' == '':
                        x = main()
			print x
                        print '----------------------'
                        print 'Length:\t'+str(len(x))
                        print 'Text:\t"'+x[0]+'"'
			if len(x) > 1:
	                        print 'Bars:\t"'+x[1]+'"'
                        print '----------------------'
                        sleep(1)
        else:           
                x = main()      
                print '----------------------' 
                print 'Length:\t'+str(len(x))
                print 'Text:\t"'+x[0]+'"'
                print 'Bars:\t"'+x[1]+'"'
                print '----------------------'
