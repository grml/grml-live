#!/usr/bin/python
"""
szs/load - a load and cpu usage module for SZS a statusbar script for WMI



CHANGELOG:

   v0.4    2004-12-14
   		* some cleanups
		* added support for 2.4 Kernels

   v0.3    2004-11-26  
		* implemented configurable label
		* some cleanups
   
   v0.2    2004-11-26  
		* implemented cpu/io utilisation

   v0.1    2004-11-24  
        * initial Release
		* implemented system load


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
import szstoolbox


# init
oldcpusum = oldcpuutil = oldioutil = 0

# load configuration
cfg = szstoolbox.CFG('load')
loadlabel = cfg.read('loadlabel')
cpulabel = cfg.read('cpulabel')
showcpu = int(cfg.read('showcpu'))
maxload = int(cfg.read('maxload'))



def main():
	global oldcpusum
	global oldcpuutil
	global oldioutil
	bars = [] 

	# cpu
	if showcpu:
		file = open('/proc/stat')
		values = [int(it) for it in file.readline().split()[1:]]
		file.close()
		newcpusum = newcpuutil = newioutil = 0
		for it in values: newcpusum += it
		for it in values[:3]: newcpuutil += it
		if szstoolbox.kernel_version[:3] == '2.6':
			for it in values[4:]: newioutil += it
		cpusum = newcpusum - oldcpusum
		bars.append(str((newcpuutil - oldcpuutil) * 100 / cpusum) + '%')
		if szstoolbox.kernel_version[:3] == '2.6':
			bars.append(str((newioutil - oldioutil) * 100 / cpusum) + '%' + cpulabel)
		oldcpusum = newcpusum
		oldcpuutil = newcpuutil
		oldioutil = newioutil
	
	# load
	if maxload > 0:
		load = os.getloadavg()
		for it in load:
			bars.append(str(int(it / maxload * 100)) + '%')
		bars[-1] += loadlabel 

	returnli =  ['']
	returnli.extend(bars)
	return returnli



if __name__ == '__main__':
	import time

	while True:
		print main()
		time.sleep(szstoolbox.interval)

