#! /usr/bin/perl -w
$^W = 1; # same as -w above

# (C) Copyright 2003 Rahul Dhesi, All rights reserved.
#
# "As is" -- No warranty.
#
# Copying, use, and modification are permitted, governed by
# the GNU General Public License, by only those who agree
# to use this program at their own risk.

use strict;

use Digest::MD5;

# unbuffered output is usually desired
$| = 1;

# $Source: /mi/maincvs/mail/postfix.transform.log,v $
# $Id: postfix.transform.log,v 1.4 2003/01/19 23:55:58 dhesi Exp $
#
# Transform postfix log, adding a PMID field to each line.

$::myname = $0;
$::myname =~ s|.*/||;

$::RCSHEADER = '$Source: /mi/maincvs/mail/postfix.transform.log,v $' . "\n" .
	'$Id: postfix.transform.log,v 1.4 2003/01/19 23:55:58 dhesi Exp $';

# suppresss perl warnings
$::debug = $::opt_x = undef;
$::ddebug = $::opt_X = undef;
$::verbose = $::opt_v = undef;
$::trace = $::opt_t = undef;
$::opt_h = undef;

$::usage = "usage: $::myname [-vtx] [ file ... ] (or -h for help)";
if (@ARGV && $ARGV[0] =~ "^-.+" ) {
  local($^W) = 0;		# suppress annoying undef warnings
  require "getopts.pl";
  &Getopts("vtxXhZ");		# Z will suppress perl warning
}

$::ddebug = $::opt_X;			# debug
$::debug = $::opt_x || $::ddebug;	# extended debug
$::trace = $::opt_t;
$::verbose = $::debug || $::trace || $::opt_v;
if ($::opt_h) {
  &givehelp();
  exit(0);
}

## (@ARGV < 1) && &usage_error;

my %pmid;
my %pending;

# program goes here
while (<>) {
  # Dec  3 00:51:42 mauve pf2/cleanup[8080]: 496FC2B888: message-id=<37593.697082511571400.3964@localhost>
  if (/
    ^						# beginning of line
    .{15}					# 15-char timestamp
    \s						# blank
    \S+						# hostname
    \s						# blank
    [^\s\[]+					# postfix syslog name
    \[ \d+ \]					# [pid]
    \:						# colon
    \s						# blank
    ([0-9A-F]+)					# QID
    \:						# colon
    \s						# blank
    message\-id\=				# message-id=
    \< ([^\>]+) \>				# <message-id>
    \s*
    $
    /x
    ) {
      # pmid is 32-bit crc of message-id
      my $msgid = $2;
      my $qid = $1;
      my $pmid = $pmid{$qid} = Digest::MD5::md5_base64($msgid);
      # print any pending lines
      my $pending;
      for $pending (@ { $pending{$qid} } ) {
	$::ddebug && print ">> (restore) [$pmid] $pending";
	print "[$pmid] $pending";
      }
      delete $pending{$qid};
      print "[$pmid] $_";
  } elsif (
    /
    ^						# beginning of line
    .{15}					# 15-char timestamp
    \s						# blank
    \S+						# hostname
    \s						# blank
    [^\s\[]+					# postfix syslog name
    \[ \d+ \]					# [pid]
    \:						# colon
    \s						# blank
    ([0-9A-F]+)					# QID
    \:						# colon
    \s						# blank
    .*
    $
    /x
  ) {
    my $msgid = $1;
    if (defined($pmid{$msgid})) {
      print "[$pmid{$1}] $_";
    } else {
      $::ddebug && print ">> (save) $_";
      push ( @ { $pending{$msgid} }, $_);
    }
  }
}

sub usage_error {
  my($msg) = @_;
  if ($msg) {
    die "$msg\n";
  } else {
    die "$::usage\n";
  }
}

sub givehelp {
   ## require 'local/page.pl';
   ## &page(<<EOF);
   print <<EOF;
$::usage

Requires the DIgest::MD5 module from CPAN.

Reads Postfix syslogs from stdin or argument filenames.  Writes to stdout.

Prefixes each output line with BASE64 MD5 value for the message-id
corresponding to each line.

Tested only with input logs from a Linux syslog for:
  Postfix snapshot 20021101
  Postfix 2.0.2.

"As is" -- No warranty.  Licensed per the GNU General Public License --
see terms inside the source file.

  -v		Be verbose.
  -t		Trace only -- show what would be done but don't do it.
  -x		Enable debugging -- for program maintainers.
  -X		Enable more debugging -- for program maintainers.

$::RCSHEADER
EOF
}

