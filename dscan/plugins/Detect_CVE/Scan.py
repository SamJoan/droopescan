from dscan.plugins.Detect_CVE import ultilities as ulti
import requests
import re
import string
import random
import sys
import time
import urllib3
from dscan.plugins.Detect_CVE.Scan_7600 import check_CVE_7600
from dscan.plugins.Detect_CVE.Scan_2019 import isVuln
from functools import partial
from random import randint
from multiprocessing import Pool
import optparse
# Start timer
start = time.time()
urllib3.disable_warnings()


def isVulnerable(host, version):
    #host = "http://"+lines.strip().split("|")[0]+"/"
    #version = lines.strip().split("|")[1]
    print ("")
    print ("[+] Check CVE-2018-7600:")    
    # check CVE 2018-7600
    check, status = check_CVE_7600(host, version)
    if (check is True):
        print(host, "|VULNERABLE|","CVE-2018-7600")
    elif(status != ""):
        print(host , " " + status)
    else:
        print(host , "|N/A|\n" )
                    
    print ("="*20)
   
    # Check CVE 2019-6340
    print ("[+] Check CVE-2019-6340:")
    check, status = isVuln(host)
    if (check is True):
        print(host , "|VULNERABLE|","CVE-2019-6340")
    elif(status == "NODE"):
        print(host,"|NODE_AVAILABLE|\n")
    else:
        print(host, "|N/A|\n")

    print ("="*20)


