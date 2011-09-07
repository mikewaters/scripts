#!/usr/bin/env python

'''
Slurp a data file into IEM subscribers
'''

import brewery


if __name__ == '__main__':

    import argparse
    import sys

    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument('-f', '--file', required=True)
    parser.add_argument('-u', '--user', default='root')
    parser.add_argument('-p', '--password')
    parser.add_argument('-h', '--host', default='localhost')
    parser.add_argument('-d', '--field-desc')

    args = parser.parse_args()

    field_desc = [["email", "string"],
                  ["first", "string"],
                  ["last", "string"],
                  ["address", "string"],
                  ["city", "string"],
                  ["state", "string"],
                  ["zipcode", "string"],
                  ["phone", "string"],
                  ["dob", "date"],
                  ["gender", "string"],
                  ["optin_timestamp", "time"],
                  ["optin_ip", "string"],
                  ["optin_source", "string"]]
    
