#!/usr/bin/env python

'''
Alter all tables in a database to use another storage engine.
'''

import MySQLdb
import MySQLdb.cursors

class MySQLConn(object):

    def __init__(self, username='root', password='', database=None, cursor=None):
        """
        Initialize generic MySQL connection object.

        """
        self.connection = self._mysql_connect(database, username, password)
        self.cursor = self.connection.cursor(cursor)

    def execute(self, query, fetchall=True, warn_only=False):
        """
        Execute a command on the connection.
        query: SQL statement.

        """
        try:
            self.cursor.execute(query)
            self.connection.commit()
        except MySQLdb.Error, e:
            self.connection.rollback()
            print "MySQL Error %d: %s" % (e.args[0], e.args[1])
            if not warn_only:
                raise
        except MySQLdb.Warning, w:
            print "MySQL Warning: %s" % (w)
        if fetchall:
            return self.cursor.fetchall()
        else:
            return self.cursor.fetchone()

    def close(self):
        """
        Close database connection.

        """
        self.cursor.close()
        self.connection.close()

    def _mysql_connect(self, database, username, password):
        """
        Return a MySQL connection object.

        """
        try:
            conn = {'host': 'localhost',
                    'user': username,
                    'passwd': password}

            if database:
                conn.update({'db': database})

            return MySQLdb.connect(**conn)

        except MySQLdb.Error, e:
            print "MySQL Error %d: %s" % (e.args[0], e.args[1])
            raise

def convert_to_engine(uid, passwd, database, engine):
    """
    Convert all table engines to {engine} (if possible).

    """
    if engine.lower() == 'innodb':
        engine = "InnoDB"
    elif engine.lower() == "myisam":
        engine = "MyISAM"
    else:
        print "unsupported engine %s." % engine
        return
    
    db = MySQLConn(username=uid, password=passwd, cursor=MySQLdb.cursors.DictCursor)
    tables = db.execute("SELECT TABLE_NAME AS name, ENGINE AS engine " + \
                        "FROM information_schema.TABLES "+ \
                        "WHERE TABLE_SCHEMA = '%s'" % database)
    print tables
    print "altering the following tables:"
    found = False
    for table in tables:
        if table.get('engine') != engine:
            found = True
            print "\t%s" % table

    if found is False:
        print "\tnone. goodbye."
        return

        
    for table in tables:
        if table.get('engine') != engine:
            db.execute("ALTER TABLE %s.%s ENGINE='%s'" % (database, table.get('name'), engine))
            
    db.close()

if __name__ == "__main__":

    import sys
    
    if len(sys.argv) != 4:
        sys.exit("usage: %s user database engine" % sys.argv[0])

    uid, db, engine = sys.argv[1:]
    passwd = raw_input("enter mysql password:")

    convert_to_engine(uid, passwd, db, engine)

