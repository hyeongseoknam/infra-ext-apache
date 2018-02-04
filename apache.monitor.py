#!/usr/bin/python
import glob, os, sys, signal, pwd, time
from StringIO import StringIO
import requests

def printHistory(name, key, value, buf):
    buf.write('H "')
    buf.write(name)
    buf.write('" "apache.perf.')
    buf.write(key.replace(' ','_').lower())
    buf.write('" ')
    buf.write(str(value))
    buf.write('\n')

def printMeta(name, key, value, buf):
    buf.write('M "')
    buf.write(name)
    buf.write('" "apache.attr.')
    buf.write(key.replace(' ','_').lower())
    buf.write('" "')
    buf.write(str(value).strip())
    buf.write('"\n')

import socket
hostname= socket.gethostbyname(socket.gethostname())
def parse_scoreboard(scoreboard):
    """ Parses scoreboard """

    keys = {
        '_': 'WaitingForConnection',
        'S': 'StartingUp',
        'R': 'ReadingRequest',
        'W': 'SendingReply',
        'K': 'KeepaliveRead',
        'D': 'DNSLookup',
        'C': 'ClosingConnection',
        'L': 'Logging',
        'G': 'GracefullyFinishing',
        'I': 'Idle',
        '.': 'OpenSlot'
    }

    scores = {}
    for score in scoreboard:
        if score in keys:
            key = keys[score]
            if key in scores:
                scores[key] += 1
            else:
                scores[key] = 1

    return scores

def measurePerformance(name=hostname, host='127.0.0.1', port=80, username=None, password=None, buf=None ):
    r= requests.get('http://%s:%d/server-status?auto'%(host,port) )
    if r.status_code < 300:
        for line in r.text.split("\n"):
            if ':' in line:
                key = line[0:line.find(':')]
                value = line[line.find(':')+1:]
                if key == 'Scoreboard':
                    for sk, sv in parse_scoreboard(value.strip()).iteritems():
                        printHistory(name, sk, sv, buf)
                else:
                    try:
                        printHistory(name, key.strip().replace(' ', '_'), float(value.strip()), buf)
                    except:
                        printMeta(name, key, value, buf)




def listdir(prefix=os.path.split(os.path.realpath(__file__))[0]):
    buf = StringIO()
    for filepath in glob.glob('%s/config/*.conf'%(prefix)):
        f= open(filepath,'r')
        if f:
            arg_dict = {}
            for line in f.readlines():
                if '=' in line:
                    k, v = line.strip().split('=')
                    arg_dict[k] = v
            try:
                measurePerformance(buf=buf, **arg_dict)
            except :
                pass
    return buf.getvalue()




def serve(host = '127.0.0.1', port=54000):
    from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer
    import os
    import re
    class MyHandler(BaseHTTPRequestHandler):
        def _doSend(self, response_text):
            self.send_response(200)
            self.send_header('Content-type', 'plain/text')
            self.end_headers()

            self.wfile.write(response_text)

        def do_GET(self):
            self._doSend(listdir())

            return
    try:
        server = HTTPServer((host, port), MyHandler)

        server.serve_forever()

    except KeyboardInterrupt:
        print('^C received, shutting down the web server')
        server.socket.close()

def redirectstdouterror( logfileprefix ):
    sys.stdout = open ( logfileprefix+'.out', 'a+' )
    sys.stderr = open ( logfileprefix+'.err', 'a+' )


def daemonize(uid = os.getuid(), log_prefix = None, port=54001):
    if not hasattr ( os, 'fork'):
        return
    if os.fork():
        # os._exit(0)
        return

    os.setsid()
    os.setuid( uid )
    signal.signal(signal.SIGHUP, signal.SIG_IGN)

    if os.fork():
        os._exit(0)

    sys.stdin = open("/dev/null", "r")
    if log_prefix:
        redirectstdouterror ( log_prefix )
    else:
        sys.stdout = open("/dev/null", "w")
        sys.stderr = open("/dev/null", "w")
    serve(port=54001)

def remotemeasure(host='127.0.0.1', port=54001):
    try:
        r = requests.get('http://%s:%d'%(host, port), timeout=300)
        sys.stdout.write(r.text)
    except (requests.exceptions.Timeout, requests.exceptions.ConnectionError):
        daemonize(port=port)
        time.sleep(3)
        r = requests.get('http://%s:%d' % (host, port), timeout=300)
        sys.stdout.write(r.text)

if __name__ == '__main__':
    #remotemeasure()
    print listdir()
