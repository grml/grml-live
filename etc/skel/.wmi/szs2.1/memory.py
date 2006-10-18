#!/usr/bin/python
"""
szs/memory - a RAM and swap usage module for SZS a statusbar script for WMI



CHANGELOG:

   v0.3    2004-12-14
		* some cleanups
		* added linux 2.4 support
   
   v0.2    2004-11-26  
		* implemented swap usage
		* implemented RAM usage
		* implemented configurable labels
		* some cleanups

   v0.1    2004-11-24  
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

import szstoolbox



# load configuration
cfg = szstoolbox.CFG('memory')
label = cfg.read('label')
showram = int(cfg.read('showram'))
showswap = int(cfg.read('showswap'))



def main():
	bars = [] 
	file = open('/proc/meminfo')
	values = [it.split()[1] for it in file.readlines()]
	file.close()

	# RAM
	if showram:
		if szstoolbox.kernel_version[:3] == '2.6':
			bars.append('' + str((int(values[0]) - int(values[1]) - int(values[2]) - int(values[3])) * 100 / int(values[0])) + '%')
		else:
			bars.append('' + str((int(values[3]) - int(values[4]) - int(values[6]) - int(values[7])) * 100 / int(values[3])) + '%')

	# swap
	if showswap and int(values[11])>0:
		if szstoolbox.kernel_version[:3] == '2.6':
			bars.append(str((int(values[11]) - int(values[12])) * 100 / int(values[11])) + '%')
		else:
			bars.append(str((int(values[15]) - int(values[16])) * 100 / int(values[15])) + '%')

	# label
	if showram or (showswap and int(values[11])>0):
		bars[-1] +=  label
		
	returnli =  ['']
	returnli.extend(bars)
	return returnli



if __name__ == '__main__':
	import time

	while True:
		print main()
		time.sleep(szstoolbox.interval)

