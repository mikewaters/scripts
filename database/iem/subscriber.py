
'''
iem subscriber stuff
'''

import MySQLdb as mysql
import csv
import time
from lepl.apps.rfc3696 import Email
import random

def cfid(fieldname):
    '''
    our current email_customfields id->name mapping:
    '''
    fieldmap = {'title': 1, 'first': 2, 'last': 3, 'phone': 4, 'mobile': 5,
            'fax': 6, 'dob': 7, 'city': 8, 'state': 9, 'zipcode': 10,
            'optindate': 13, 'optinip': 14, 'gender': 15,'domain': 17,
            'username': 18}

    return fieldname[fieldname]


datafile = '/var/www/iem61/admin/import/route72_clean_region1.csv'
#datafile = '/tmp/route72-test.tsv'

user = 'iem'
passwd = 'iem1234'
host = 'localhost'
db = 'iem61'
prefix = 'email_'
listid = 1

fields = ('email', 'first', 'last', 'state', 'zipcode', 'dob', 'domain')
optindate = int(time.time())
optinip = None
delimiter = "\t"

batchsz = 1000

conn = mysql.connect(host=host, user=user, passwd=passwd, db=db)
try:
    cur = conn.cursor()

    cur.execute("SELECT subscribecount FROM %slists WHERE listid=%d" % (prefix,listid))
    scnt = int(cur.fetchone()[0])
    print "connected. subscribercount for list %d is %s" % (listid, scnt)

    start_ts = int(time.time())

    def is_bad(email, listid, domain):

        # we're using Duplicate Key exceptions/ INSERT IGNORE rather than check for IsDuplicate();
	# this also will weed out unsubs (b/c an unsub will be in there... if
	# we werent ignoring dupes we'd need to deal with this.

        # check banned
	# assuming global ('g') ban.
	if domain:
            sql = "SELECT banid FROM %sbanned_emails WHERE emailaddress='%s'" % (prefix, domain)
	    cur.execute(sql)
	    if cur.fetchone() != None:
		return True

	sql = "SELECT banid FROM %sbanned_emails WHERE emailaddress='%s'" % (prefix, email)
	cur.execute(sql)
	if cur.fetchone() != None:
	    return True

        return False
    
    is_valid = Email()

    data = csv.DictReader(open(datafile, 'rb'), fieldnames=fields, delimiter=delimiter)

    print "starting import"
    inserted = 0
    total = 0
    for line in data:
        
        email = line['email']
	domain = line['domain']        
        if is_valid(email) and not is_bad(email, listid, domain):
                
            ts = int(time.time())
            confirmcode = "%032x" % random.getrandbits(128)
	    domain = line['domain']
                          
            sql = """INSERT IGNORE INTO %slist_subscribers(listid, emailaddress, format, confirmed, \
confirmcode, subscribedate, bounced, unsubscribed, requestdate, requestip, \
confirmdate, confirmip, formid, domainname) VALUES (%d, '%s', 'b', 1, '%s', '%s', \
0, 0, '%s', '%s', '%s', '%s', 0, '%s')""" % (prefix, listid, email, confirmcode, ts, optindate, optinip, ts, '', domain)

            try:
                cur.execute(sql)

                # custom fields
                subscriberid = cur.lastrowid
		
		
                conn.commit()
                inserted += 1
                total += 1
   
            except Exception as e:
	        # ignore 'Duplicate key'... we are using this to weed out dupes
	        # CUT - using INSERT IGNORE instead
                #if e.args[0] != '1062'
                #    print str(e)
		#    print data.line_num
		#    print
		print str(e)
		print email, data.line_num

                conn.rollback()

    	    if inserted % batchsz == 0:
                sql = "UPDATE %slists SET subscribecount=subscribecount + %d WHERE listid=%d" % (prefix, inserted, listid)
                try:
		    cur.execute(sql)
	            conn.commit()
		    inserted = 0
		    print "inserted batch of %d" % batchsz

		except Exception as e:
		    print str(e)
		    print

    		    conn.rollback()

    end_ts = int(time.time())

    cur.execute("SELECT subscribecount FROM %slists WHERE listid=%d" % (prefix, listid))
    sfinalcnt = int(cur.fetchone()[0])
    print "instered %d records; subscribecount is now %s (was %s, diff %s)" % (total, sfinalcnt, scnt, sfinalcnt - scnt)
    print "elapsed time was %s seconds" % (end_ts - start_ts)

except Exception as e:
    print str(e)
    
finally:
    conn.close()
