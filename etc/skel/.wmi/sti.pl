#!/usr/bin/perl

# STI - StatusText Improved ;) 
# A simple program to update the bartext in WMI
# last modified: 20 June 2004

# Copyright (C) 2004 Nicholas Lativy

# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA

# To use this program put it in a directory in your $PATH 
# make executable and put the following lines in your ~/.xinitrc file:
#  sti &
#  wmi

use strict;

# The 4 following variables should be set by the user
#--------------------------------------------------
# my $TFORMAT = "%a %d %B - %H%M"; # time format (see man date)
#-------------------------------------------------- 
my $TFORMAT = "%D - %H:%M";
my $MAILDIR = "~/mail/inbox";   # location of user maildir
#my $TOTALMEM = 256;              # physical memory in MB
my $TOTALMEM = `free -mt | grep Mem | cut -b16-20`;
my $RTIME = 5;                   # time between each refresh of stats
# note that the actual time between each refresh will be at least 1/2
# a second longer than $RTIME

for (;;) {
   my ($mail, $new) = &check_mail($MAILDIR);
   my ($mem_used, $cpu_used) = &sys_stats($TOTALMEM);
   my $time = &get_time($TFORMAT);
   system "wmiremote -t \"[$cpu_used% MEM: $mem_used%]  [$mail mail, $new new]  [$time]\"";
   #system "wmiremote -t \"[CPU: $cpu_used% MEM: $mem_used%]  [$mail mail, $new new]  [$time]\"";
   #print "[CPU: $cpu_used% MEM: $mem_used%]  [$mail mail, $new new]  [$time]\n"; # this line was for testing
   sleep $RTIME;
}

sub check_mail {
   # check the user's email
   # currently only supports maildir
   my ($mail) = @_;
   chomp(my $cur = `ls $MAILDIR/cur | wc -l`);
   chomp(my $new = `ls $MAILDIR/new | wc -l`);
   return($cur + $new, $new);
}

sub get_time {
   # get the localtime, currently using the date
   # command. change it to use perl's localtime?
   my ($format) = @_;
   chomp(my $date = `date "+${TFORMAT}"`);
   return($date);
}

sub sys_stats {
   # get % of CPU and memory used
   my ($mem) = @_;
   chomp(my $mem_free = `free -mt | grep Mem | cut -b38-40`);
   chomp(my $cpu_idle = `uptime`);
#   chomp(my $cpu_idle = `top -bn2d0.5 | grep Cpu | tail -n1`);
#   $cpu_idle =~ /(\d+\.\d+)%(\s)idle/;
#   $cpu_idle = $1;
#   my $cpu_used = 100 - $cpu_idle;
   my $cpu_used = $cpu_idle;
   my $mem_used = 100 - $mem_free / $mem * 100;
   # return rounded up figures
   return (sprintf("%.0f",$mem_used), sprintf($cpu_used));
}
