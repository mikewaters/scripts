#!/usr/bin/env python

'''
spit a csv file into N appropriately-named pieces.
'''

import argparse
import os.path

parser = argparse.ArgumentParser()
parser.add_argument('-f', '--file', required=True)
parser.add_argument('-l', '--lines', required=True)
args = parser.parse_args()

def batch_iterator(iterator, batch_size) :
    """Returns lists of length batch_size.
    """
    entry = True #Make sure we loop once
    while entry :
        batch = []
        while len(batch) < batch_size :
            try :
                entry = iterator.next()
            except StopIteration :
                entry = None
            if entry is None :
                #End of file
                break
            batch.append(entry)
        if batch :
            yield batch


with open(args.file, 'r') as f:
    iter = 1
    for chunk in batch_iterator(f, int(args.lines)):
	chunk = ''.join(chunk)
	name, ext = os.path.splitext(args.file)
	with open("%s_%s%s" % (name, str(iter), ext), 'w') as of:
	    of.write(chunk) 
	    iter += 1
