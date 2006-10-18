# Filename:      .irbrc
# Purpose:       configuration file for irb (interactive ruby)
# Authors:       grml-team (grml.org), (c) Michael Prokop <mika@grml.org>
# Bug-Reports:   see http://grml.org/bugs/
# License:       This file is licensed under the GPL v2.
# Latest change: Die Sep 26 23:16:29 CEST 2006 [mika]
################################################################################

# we want to be able to use tab-completion in irb:
require 'irb/completion'
ARGV.concat [ "--readline", "--prompt-mode", "simple" ]

# we want to get a history file of our session:
module Readline
  module History
    LOG = "#{ENV['HOME']}/.irb-history"

    def self.write_log(line)
      File.open(LOG, 'ab') {|f| f << "#{line}\n"}
    end

    def self.start_session_log
      write_log("\n# session start: #{Time.now}\n\n")
      at_exit { write_log("\n# session stop: #{Time.now}\n") }
    end
  end

  alias :old_readline :readline
  def readline(*args)
    ln = old_readline(*args)
    begin
      History.write_log(ln)
    rescue
    end
    ln
  end
end

Readline::History.start_session_log

# simple prompt?
# IRB.conf[:PROMPT_MODE] = :SIMPLE

# prompt for easy copy/paste? start with irb --prompt xmp
IRB.conf[:PROMPT][:XMP][:RETURN] = "\# => %s\n"

# copy/paste from manpage:
# IRB.conf[:IRB_NAME]="irb"
# IRB.conf[:MATH_MODE]=false
# IRB.conf[:USE_TRACER]=false
# IRB.conf[:USE_LOADER]=false
# IRB.conf[:IGNORE_SIGINT]=true
# IRB.conf[:IGNORE_EOF]=false
# IRB.conf[:INSPECT_MODE]=nil
# IRB.conf[:IRB_RC] = nil
# IRB.conf[:BACK_TRACE_LIMIT]=16
# IRB.conf[:USE_LOADER] = false
# IRB.conf[:USE_READLINE] = nil
# IRB.conf[:USE_TRACER] = false
# IRB.conf[:IGNORE_SIGINT] = true
# IRB.conf[:IGNORE_EOF] = false
# IRB.conf[:PROMPT_MODE] = :DEFALUT
# IRB.conf[:PROMPT] = {...}
# IRB.conf[:DEBUG_LEVEL]=0
# IRB.conf[:VERBOSE]=true

## END OF FILE #################################################################
