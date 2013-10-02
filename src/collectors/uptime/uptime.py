# coding=utf-8

"""
Uses /proc/uptime to get system uptime and idletime

#### Dependencies

 * /proc/uptime

"""

import diamond.collector
import os

class UptimeCollector(diamond.collector.Collector):
    PROC = '/proc/uptime'

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
        if os.access(self.PROC, os.R_OK):
            uptimeFile = open(self.PROC)
            times = uptimeFile.readline().strip().split(" ")
            uptimeFile.close()

            uptime = float(times[0])
            idletime = float(times[1])

            self.publish('up', uptime)
            self.publish('idle', idletime)

