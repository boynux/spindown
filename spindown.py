#!/bin/python
import os
import sys
import time
import commands
import subprocess
import pickle

LOCK = '/var/run/spindown/%s.pid.lock'
STATE = '/var/run/spindown/%s.state'

class SpinDown:
    _IDENTIFIERS = ('name', 'uuid', 'label')
    _STATES = ('idle', 'active', 'standby')
    _LOCK_FILE = 'spindown.lck'
    _STATS_DUMP = 'spindown.stats'
    
    def __init__ (self, device_id):
        self.identifier, self.device_id = self._parse_device_id (device_id)

        try:
            with open("/tmp/%s" % SpinDown._STATS_DUMP, 'r') as stats:
                self._last_stats = pickle.load (stats)
        except IOError:
            self._last_stats = None

        self.is_active = True

    def _parse_device_id (self, device_id):
        if device_id.find ('=') == -1:
            identifier, id = 'name', device_id
        else:
            parts = device_id.split ('=')
            if len (parts) != 2:
                raise Exception ("can not parse device id infomation [%s]" % device_id)
            
            identifier, id = parts

            if identifier not in self._IDENTIFIERS:
                raise Exception (
                    "Provided device indentifier [%s] is not supported, please use [%s]",
                    identifier, 
                    ', '.join (self._IDENTIFIERS)
                )

        return identifier, id

    def _find_device_path (self):
        if self.identifier == 'name':
            path = '/dev/%s' % self.device_id
        elif self.identifier == 'uuid':
            path = os.path.realpath ('/dev/disk/by-uuid/%s' % self.device_id)
        elif self.identifier == 'label':
            path = os.path.realpath ('/dev/disk/by-label/%s' % self.device_id)
        
        dirname = os.path.dirname (path)
        block_name = os.path.basename (path)[0:3]

        return "%s/%s" % (dirname, block_name)
    
    def check_state (self):
        if self._last_stats != None:
            state =  self._STATES [0 if self._last_stats == self._get_stats () else 1]
        else:
            state = self._STATES[1]

        if state != SpinDown._STATES[0]:
            try:
                os.unlink ("/tmp/%s" % SpinDown._LOCK_FILE)
            except OSError:
                pass

        self._last_stats = self._get_stats ()

        return state

    def _get_stats (self):
        stats_path = '/sys/block/%s/stat'

        block_name = os.path.basename (self._find_device_path())

        try:
            stat = open (stats_path % block_name).readline ()

            with open("/tmp/%s" % SpinDown._STATS_DUMP, 'w') as stats:
                pickle.dump (stat, stats)
        except:
            stat = None
        
        return stat

    def spin_down (self):
        state = self.check_state ()

        if state == self._STATES[0] and not os.path.isfile ("/tmp/%s" % SpinDown._LOCK_FILE):
            print "[%s] device state is [%s]. spinning down ..." % (self._find_device_path (), state)

            args = [
                commands.getoutput ('which sdparm'),
                "--flexible",
                "--command=sync",
                "--command=stop",
                self._find_device_path ()
            ]
        
            subprocess.call (args)

            with open ("/tmp/%s" % SpinDown._LOCK_FILE, 'w') as lck:
                lck.write ("%d" % os.getpid())

spinDown = SpinDown ('uuid=4FFEB3B3409EDCCD')
spinDown.spin_down ()
