# coding=utf-8

"""
Uses /proc/uptime to get system uptime and idletime

#### Dependencies

 * /proc/uptime

"""

import diamond.collector

class UptimeCollector(diamond.collector.Collector):
    def get_default_config(self):
        """
        Returns the default collector settings
        """
        config = super(UptimeCollector, self).get_default_config()
        config.update({
            'path':     'uptime'
        })

        return config

    def collect(self):
        PROC = '/proc/uptime'

        with open(PROC, 'r+b') as procFile:
            line = procFile.readline()
            uptime, idletime = [ float(val) for val in line.strip().split(" ") ]

            self.publish('up', uptime)
            self.publish('idle', idletime)

