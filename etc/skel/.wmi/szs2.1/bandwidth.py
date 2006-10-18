#!/usr/bin/python
"""
szs/bandwidth - a bandwidth module for SZS an statusbar script for WMI


CHANGELOG:

   v0.5    2004-12-14
		* some cleanups
		* removed re dependency for performance reasons

   v0.4    2004-11-29
		* replaced script interval with real interval
		* added empirical max down/up rate
		* fixed: crash if interface is down

   v0.3    2004-11-26
		* added configurabel labels
		* fixed get up packets instead of bytes bug
		* some cleanups

   v0.2    2004-11-24
   		* fixed bug with /proc/net/dev parsing
    	* adapted to the szs module interface
		* added szs.cfg support
		* use now correct interval from szs config

   v0.1    2004-10-20  
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

import os
import time
import szstoolbox



count = 0



class Interface:
		
	changetime = 0

	def __init__(self, label, downmax=1, upmax=1, down=0, up=0):
		self.label = label
		self.downmax = downmax * 1024 
		self.upmax = upmax * 1024
		self.down = down
		self.up = up

	def get_down_speed(self, down):
		old = self.down
		self.down = down
		downrate = (down - old) / interval
		if downrate > self.downmax and count > 1: 
			self.downmax = downrate
			msg.debug(self.label + ' newmax down [kB]: ' + str(self.downmax/1024), 3)
		return 100 * downrate /  self.downmax
	
	def get_up_speed(self, up):
		old = self.up
		self.up = up
		uprate = (up - old) / interval
		if uprate > self.upmax and count > 1: 
			self.upmax = uprate
			msg.debug(self.label + ' newmax up [kB]: ' + str(self.upmax/1024), 3)
		return 100 * uprate /  self.upmax



def get_data():
	global interval

	#get interval
	changetime = time.time()
	interval = changetime - Interface.changetime
	Interface.changetime = changetime
	
	# get data
	fd = open('/proc/net/dev')
	data = {}
	for it in fd.read().split('\n')[2:-1]:
		it = str(it[:6] + ' ' + it[7:]).split()
		if (len(it) > 2) and (it[0] in ifs): 
			data[it[0]] = it[1], it[9]
	fd.close()
	for it in ifs:
		if it not in data.keys():
			data[it] = 0, 0
			print it + ' is down'
	return data
	


def main():
	global count
	data = get_data()
	returnli = ['']
	for it in ifs:
		returnli.append(str(int(ifsdata[it].get_down_speed(int(data[it][0])))) + '%')
		returnli.append(str(int(ifsdata[it].get_up_speed(int(data[it][1])))) + '%' + ifsdata[it].label)
		
	count += 1
	return returnli



# load configuration
msg = szstoolbox.MSG()
cfg = szstoolbox.CFG('bandwidth')
ifs = cfg.read('ifs').split(',')
ifsdata = {}
for it in ifs:
	it = it.split(':')
	if len(it) == 4:
		ifsdata[it[0]] = Interface(it[1], int(it[2]), int(it[3]))	
	else:
		ifsdata[it[0]] = Interface(it[1])	
ifs = [it.split(':')[0] for it in ifs]



if __name__ == '__main__':
	import time

	while True:
		print main()
		time.sleep(szstoolbox.interval)
