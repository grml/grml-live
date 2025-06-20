use strict;
use IO::Handle;
use vars qw($VERSION %IRSSI);

use Irssi;
$VERSION = '0.3.3';
%IRSSI = (
	authors     => 'Jeroen Coekaerts, Koenraad Heijlen',
	contact     => 'vipie@ulyssis.org, jeroen@coekaerts.be',
	name        => 'osd',
	description => 'An OnScreenDisplay (osd) it show\'s who is talking to you, on what IRC Network.',
	license     => 'BSD',
	url         => 'http://vipie.studentenweb.org/dev/irssi/',
	changed     => '2004-01-09'
);


#--------------------------------------------------------------------
# Public Variables
#--------------------------------------------------------------------
my %myHELP = ();

#--------------------------------------------------------------------
# Help function
#--------------------------------------------------------------------
sub cmd_help { 
	my ($about) = @_;

	%myHELP = (
		osd_test => "
osd_test

Displays a small test message on screen
",

		osd => "
OSD 

You can display on screen who is paging/msg'ing you on IRC.

When you CHANGE the settings you SHOULD use /osd_reload to let these changes
take effect.

Settings:
---------

* osd_showactivechannel	(default: yes)
Currently the setting is: " . Irssi::settings_get_str('osd_showactivechannel') . "

When set to yes, OSD will be triggered even if the channel is the active channel.
When set to yes, OSD will be triggered if you send a message from your own nick.

You can test the OSD settings with the 'osd_test' command!
he 'osd_test' to test them.

",
);

	if ( $about =~ /(osd_reload|osd_test|osd)/i ) { 
		Irssi::print($myHELP{lc($1)});
	} 
}

#--------------------------------------------------------------------
# Irssi::Settings
#--------------------------------------------------------------------

Irssi::settings_add_str('OSD', 'osd_showactivechannel', "yes");

#--------------------------------------------------------------------
# initialize the pipe, test it.
#--------------------------------------------------------------------

sub init {
	osdprint("OSD Loaded.");
}

#--------------------------------------------------------------------
# open the OSD pipe
#--------------------------------------------------------------------

sub pipe_open {
    open(OSDPIPE, "| nc -q 1 localhost 1234 2>/dev/null");
	OSDPIPE->autoflush(1);
}

#--------------------------------------------------------------------
# Private message parsing
#--------------------------------------------------------------------

sub priv_msg {
	my ($server,$msg,$nick,$address,$target) = @_;
    osdprint("IRC:*private:$nick");
}

#--------------------------------------------------------------------
# Public message parsing
#--------------------------------------------------------------------

sub pub_msg {
	my ($server,$msg,$nick,$address, $channel) = @_;
	my $show;

    if ($msg =~ /$server->{nick}/) {
        osdprint("IRC:$channel:$nick");
    }
}

#--------------------------------------------------------------------
# The actual printing
#--------------------------------------------------------------------

sub osdprint {
	my ($text) = @_;
    pipe_open();
	print OSDPIPE "$text\n";
	OSDPIPE->flush();
    close(OSDPIPE);
}

#--------------------------------------------------------------------
# A test command.
#--------------------------------------------------------------------

sub cmd_osd_test {
	osdprint("Testing OSD");
}

#--------------------------------------------------------------------
# Irssi::signal_add_last / Irssi::command_bind
#--------------------------------------------------------------------

Irssi::signal_add_last("message public", "pub_msg");
Irssi::signal_add_last("message private", "priv_msg");

Irssi::command_bind("osd_test","cmd_osd_test", "OSD");
Irssi::command_bind("help","cmd_help", "Irssi commands");

#--------------------------------------------------------------------
# The command that's executed at load time.
#--------------------------------------------------------------------

init();

#--------------------------------------------------------------------
# This text is printed at Load time.
#--------------------------------------------------------------------

Irssi::print("Use /help osd for more information."); 


#- end
