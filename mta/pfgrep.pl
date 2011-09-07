#!/usr/bin/perl

################################################################################
# Rob Chanter (n137603), DS/III
# 2003-05-09
#
# pfqgrep.pl: Take the output of Postfix-style mailq, and print to stdout only
# the messages matching a pattern. Can find patterns in sender, recipient, 
# deferral reason text, or by status.
# 
# Mailq output looks like this:
# 14E67822A   1086632 Fri May  9 14:27:14  Joe_User@national.com.au
#                                          some.recipient@example.edu.au
#
# 1A18F82BB    214084 Fri May  9 14:28:08  Ted_Stoat@national.com.au
#                                          somerecipient@example.com
# History
# =======
# 2004-07-06 robc
# fixed processing of messages with multiple deferral reasons.
# added -f option to read from a file.
#
# 2003-12-23 robc
# added -v option
# 
# 2003-11-06 robc 
# First release.
#
################################################################################
# Declarations and setup.

use strict;  #oh all right then

my ($mailq,$queue_id,$size,$day,$mon,$date,$time,$sender,$sender_line);
my ($messages,$bytes);
my ($defer_reason,$recips);

# options: i to print just queue-id, s to match sender, r to match recipient,
# t to to match deferral text, a to match anywhere, q for queue name,
# h for help, d for dev mode, -v to reverse pattern match (like grep).
our ($opt_q, $opt_Q, $opt_s, $opt_r, $opt_t, $opt_a, 
	$opt_h, $opt_f, $opt_i, $opt_v); 

use Getopt::Std;
getopts('hivq:Q:s:r:a:t:f:');

#adjust these as appropriate for this machine.
if ($opt_f) {
	$mailq = $opt_f; # filename "-" is stdin.
} else {
	$mailq = "/usr/sbin/postqueue -p |";
}

$| =1;  # unbuffer I/O.

################################################################################
# START MAIN

$opt_h && showUsage();

#grab the mail queue
open(MAILQ, $mailq) or die "couldn't open mailq stream $mailq\n";

$/ = "\n\n";  #set record separator to blank line

while (<MAILQ>) {
	############################################################################
	# general setup for this time through the loop
	############################################################################
	chomp;

	# take a copy of $_ because we want to print it back out unaltered.
	my $whole_entry = $_;

	#split the queue entry into lines
	my @qinfo = split (/\n/);

	#(re)initialise some state variables for this time through...
	$defer_reason = '';
	$recips       = '';
	my $in_maildrop_queue = 0;
	my $in_incoming_queue = 0;
	my $in_active_queue   = 0;
	my $in_hold_queue     = 0;
	my $in_deferred_queue = 0;

	############################################################################
	# break the queue entry into parts and decide what queue it's in.
	############################################################################

	#clean up header/footer info from the mailq output.
	if ($qinfo[0] =~ /^-Queue ID-/) {
		#it's the first item in the queue. discard the first line.
		shift(@qinfo);
	} 
	elsif ($qinfo[0] =~ /^-- /) {
		#it's the summary line at the end. Chuck it out.
		next;
	}
	elsif ($qinfo[0] =~ /Mail queue is empty/) {
		#nothing to do
		last;
	}

	my $sender_line = shift(@qinfo);

	# grab the elements out of the first line of the mailq entry.
	my ($queue_id,$size,$day,$mon,$date,$time,$sender) = split(' ', $sender_line, 7);
	
	# the active/hold indicators are joined to the queue id 
	# in postfix >= 2.0.16-20031223
	if ($queue_id =~ s/\*//) {
		$in_active_queue = 1;
	}
	if ($queue_id =~ s/\!//) {
		$in_hold_queue = 1;
	}
	if ($sender =~ /maildrop queue/) {
		$in_maildrop_queue = 1;
	}

	# If the next line in the mailq entry has parens around it, it's a deferred 
	# message (can be (active or hold) and deferred at the same time).
	if ($qinfo[0] =~ /^\s*\(.*\)$/) {
		$defer_reason .= shift(@qinfo);
		$in_deferred_queue = 1;
	}

	# if we haven't figured out what queue it's in yet, must be incoming.
	if (!($in_active_queue or $in_hold_queue or $in_maildrop_queue or $in_deferred_queue)) {
		$in_incoming_queue = 1;
	}

	# what's left in the qinfo array is usually just the list of recipients.
	# there might also be additional deferral reasons mixed in, too.
	for (@qinfo) {
		#strip leading whitespace.
		s/^\s+//;
		#if the next line is some text in parens, it's a deferral message. 
		if (/^\(.*\)/) {
			$defer_reason .= $_;
		} else {
			$recips .= lc(" $_");
		}
	}
	$recips =~ s/^\s+//; # the first recipient we added to the list has
	                     # a leading space.

	############################################################################
	# Run through a bunch of tests to see if we should print this message
	# back out.
	############################################################################

	my $print_this = 0; #only print if we match something.

	if ($opt_a) { $print_this = 1 if $whole_entry  =~ /$opt_a/is};
	if ($opt_s) { $print_this = 1 if $sender       =~ /$opt_s/i};
	if ($opt_r) { $print_this = 1 if $recips       =~ /$opt_r/i};
	if ($opt_t) { $print_this = 1 if $defer_reason =~ /$opt_t/i};
	
	# and then reverse the meaning of the match if they used '-v'.
	if ($opt_v) {
		$print_this = $print_this ? 0 : 1;
	}
	
	#if none of the above options were set, then mark the item to be 
	#printed before we evaluate the in_mumble_queue checks.
	# (also overrides the -v thing above).
	$print_this = 1 if (!($opt_a or $opt_s or $opt_r or $opt_t));

	# Now check if they asked to see messages in a particular queue.
	if ($opt_q) {
		# they asked to include a named queue.
		if ($opt_q eq 'maildrop') { $print_this = 0 unless $in_maildrop_queue};
		if ($opt_q eq 'incoming') { $print_this = 0 unless $in_incoming_queue};
		if ($opt_q eq 'active')   { $print_this = 0 unless $in_active_queue};
		if ($opt_q eq 'hold')     { $print_this = 0 unless $in_hold_queue};
		if ($opt_q eq 'deferred') { $print_this = 0 unless $in_deferred_queue};
	}
	elsif ($opt_Q) {
		# they asked to exclude a named queue.
		if ($opt_Q eq 'maildrop') { $print_this = 0 if $in_maildrop_queue};
		if ($opt_Q eq 'incoming') { $print_this = 0 if $in_incoming_queue};
		if ($opt_Q eq 'active')   { $print_this = 0 if $in_active_queue};
		if ($opt_Q eq 'hold')     { $print_this = 0 if $in_hold_queue};
		if ($opt_Q eq 'deferred') { $print_this = 0 if $in_deferred_queue};
	}

	############################################################################
	# Now print the message back out, maybe. Print either the full queue item
	# or the queue ID.
	############################################################################

	if ($print_this) {
		# increment the accumulators for message count and byte count.
		$messages++;
		$bytes += $size;
		if ($opt_i) {
			print "$queue_id\n";
		} else {
			print "$whole_entry\n\n";
		}
	}
}

# And print a total line for the queue like the real mailq does.
# but if they asked for just queue IDs, it's probably not wanted.
if (! $opt_i) {
	my $kbytes = int($bytes/1024) || "0";
	$messages ||= "0";
	print "-- $kbytes Kbytes in $messages Requests.\n";
}

################################################################################
##  SUBROUTINES
################################################################################

sub showUsage() {
	my $msg = <<EOM ;

NAME
====
  pfqgrep.pl - Postfix queue grep.

DESCRIPTION
===========

  Show the messages from a Postfix mailq that match a specified pattern. Can
  look for the pattern in the sender address, recipient address(es), deferral
  reason text, or the whole mailq entry. Uses the output of potsqueue -p rather
  than looking directly at the spool, so that it can be run by non-root users.
  Optionally, can print just the queue ID of matching messages for input into
  postsuper or other utilities.

SYNOPSIS
========
  pfqgrep.pl [options]

  Options:
     The <pattern> passed in to the following four options is a perl-compatible
     regular expression (pcre), since this is a perl script.

  -a <pattern>           look for <pattern> anywhere in the queue item. The
                         search can span multiple lines in the queue entry (the
						 regexp has a /s switch).

  -s <pattern>           look for <pattern> in just the sender address.

  -r <pattern>           look for <pattern> in just the recipient address(es).
                         If there are multiple recipients, it is transformed to
                         a comma-separated list to be searched.

  -t <pattern>           look for <pattern> in just the deferral reason text.

  -v                     Reverse the meaning of the search. This does not affect
                         the -q or -Q options, only patterns specified with 
                         -a, -r, -s or -t.

  NOTE: The above options are additive (a logical OR) if more than one is used.
  They are also case-insensitive (the regexp has a /i switch).

  There is no sanity checking done on the pattern passed in, so use complex
  regexp's at your own risk.

  If -q or -Q is also used, they will restrict the output to messages in the
  selected queue(s). The -[qQ] options can be used alone or in combination with
  a pattern search.

  -q <queue-name>        Restrict the search to messages in the named queue.
                         <queue-name> can be one of maildrop, incoming, active,
                         hold, or deferred.

  -Q <queue-name>        Restrict the search to messages excluding the named 
                         queue. <queue-name> is as for -q above.

  -i                     Print just the queue ID of matching entries.

  -f <filename>          read mailq output from a named file instead of from
                         the mailq command. A filename of "-" is stdin.

  -h                     Print this message and exit.

EOM

	die $msg;
}

