#!/usr/bin/python

# Module to show usage of your partitions

import szstoolbox
from os import statvfs
import statvfs as vfs

def init():
	""" yeah... init wie schwein """

	global hdds,lst,ready,fstab
	cfg = szstoolbox.CFG('diskusage')
	fstabF = file('/etc/fstab','r')
	fstab = fstabF.readlines()
	fstabF.close()
	config = cfg.read('disks')
	if type(config) <> list:
		hdds = config.split(',')
	else:
		hdds = [] 
		for it in config:
			hdds.extend(it.split(','))
	hdds = [x.split(':') for x in hdds]

	# rename mountpoints into the corresponding devs				
	global fstabD
	fstabD = {}
	for x in fstab:
		x = x.strip()
		if len(x) > 1:
			if x[0] <> '#':
				x = x.strip().split()
				fstabD[x[1]] = x[0]
	for x in range(len(hdds)):
		if hdds[x][0] in fstabD.keys():
			hdds[x][0] = fstabD[hdds[x][0]]

	for x in range(len(hdds)):
		if hdds[x][0][:4] != '/dev':
			hdds[x][0] = '/dev/' + hdds[x][0]
	
	ready = True



def main():
	""" Module to show usage and capacity of disks """

	if not 'ready' in globals(): init()
	global mntD
	
	mntD = {}
	mntF = file('/etc/mtab','r')
	mnt = mntF.readlines()
	mntF.close()
	for x in mnt:
		x = x.split()
		mntD[x[0]] = x[1]
	
	lst = []
	for hdd in hdds:
		if hdd[0] in mntD:
			stat = statvfs(mntD[hdd[0]])
			blocks = stat[vfs.F_BLOCKS]
			free = stat[vfs.F_BFREE]
			lst.append(str((blocks-free)*100/blocks)+'%'+hdd[1])
	
	return ['',','.join(lst)]



if __name__ == '__main__':
	""" helps to debug the script """

	from sys import argv
	from time import sleep

	print main()
	if 'loop' in argv:
		while '' == '':
			x = main()
			print '----------------------'
			print 'Length:\t'+str(len(x))
			print 'Text:\t"'+x[0]+'"'
			print 'Bars:\t"'+x[1]+'"'
			print '----------------------'
			print '/proc/mounts:'
			for x in mntD:
				print str(x)+':\t'+str(mntD[x])
	
			print ''
			print '/etc/fstab:'
			for x in fstabD:
				print str(x)+':\t'+str(fstabD[x])
			sleep(1)
	else:
		x = main()
		print '----------------------'
		print 'Length:\t'+str(len(x))
		print 'Text:\t"'+x[0]+'"'
		print 'Bars:\t"'+x[1]+'"'
		print '----------------------'
	
		print '/proc/mtab:'
		for x in mntD:
			print str(x)+':\t'+str(mntD[x])
	
		print ''
		print '/etc/fstab:'
		for x in fstabD:
			print str(x)+':\t'+str(fstabD[x])
