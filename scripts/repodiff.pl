#!/usr/bin/perl 
# Filename:      repodiff.pl
# Purpose:       compare the available packages from two different repositories
# Authors:       grml-team (grml.org), (c) Alexander Wirt <formorer@grml.org>
# Bug-Reports:   see https://grml.org/bugs/
# License:       This file is licensed under the GPL v2 or any later version.
################################################################################
# Notice: adjust $c_file[12] according to your needs, by default the script
# compares the i386 pool with the amd64 pool of grml.
################################################################################

use strict; 
use LWP::Simple;
use Compress::Zlib ;

use AptPkg::Config '$_config';
use AptPkg::System '$_system';
use AptPkg::Version;

(my $self = $0) =~ s#.*/##;

# initialise the global config object with the default values
$_config->init;

# determine the appropriate system type
$_system = $_config->system;

# fetch a versioning system
my $vs = $_system->versioning;

sub describe
{
    return 'earlier than' if $_[0] < 0;
    return 'later than'   if $_[0] > 0;
    'the same as'; 
}

my $c_file1 = get('http://deb.grml.org/dists/grml-testing/main/binary-i386/Packages.gz'); 
my $c_file2 = get('http://deb.grml.org/dists/grml-testing/main/binary-amd64/Packages.gz');

my $file1 = Compress::Zlib::memGunzip($c_file1);
my $file2 = Compress::Zlib::memGunzip($c_file2);

my $file1_tree; 
my $file2_tree;

my ($package, $version) = "";

foreach my $line (split('\n', $file1)) {
    if ($line =~ m/^Package: (.*)/) {
	$package = $1; 
    } elsif ($line =~ m/^Version: (.*)/) {
	$file1_tree->{$package} = "$1";
    }	
}

foreach my $line (split('\n', $file2)) {
     if ($line =~ m/^Package: (.*)/) {
	$package = $1; 
    } elsif ($line =~ m/^Version: (.*)/) {
	$file2_tree->{$package} = "$1";
    }	 
}


foreach my $key (keys %{$file1_tree}) {
    if (defined $file2_tree->{$key}) {
	print "package $key version " . $file1_tree->{$key} . " on repo1 is ",
	(describe $vs->compare($file1_tree->{$key}, $file2_tree->{$key})), 
	" " . $file2_tree->{$key} . " on repo2\n"; 
    } else {
	print "$key does not exist on repo2\n"; 
     }
}

foreach my $key (keys %{$file2_tree}) {
    if (not defined $file1_tree->{$key}) {
	 print "$key does not exist on repo1\n";
    }
}

# EOF
