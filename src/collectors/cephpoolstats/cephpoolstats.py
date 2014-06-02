import subprocess
import re
import os
import sys
import shlex
import json

import diamond.collector

os.chdir(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, '../ceph')

import ceph


"""
Get ceph pool stats from one node
"""


class CephPoolStatsCollector(diamond.collector.Collector):
    def get_default_config_help(self):
        config_help = super(CephPoolStatsCollector, self).get_default_config_help()
        config_help.update({
            'socket_path': 'The location of the ceph monitoring sockets.'
                           ' Defaults to "/var/run/ceph"',
            'socket_ext': 'Extension for socket filenames.'
                          ' Defaults to "asok"',
            'ceph_binary': 'Path to "ceph" executable. '
                           'Defaults to /usr/bin/ceph.',
            'cluster_name': "Name of cluster.  Defaults to 'ceph'."
        })
        return config_help

    def get_default_config(self):
        """
        Returns the default collector settings
        """
        config = super(CephPoolStatsCollector, self).get_default_config()
        config.update({
            'socket_path': '/var/run/ceph',
            'socket_ext': 'asok',
            'ceph_binary': '/usr/bin/ceph',
            'cluster_name': 'ceph'
        })
        return config

    def _get_stats(self):
        """
        Get ceph pool stats
        """
        cmd = "%s --cluster=%s osd pool stats --format=json" % (self.config['ceph_binary'], self.config['cluster_name'])
        cmd_spl = shlex.split(cmd)

        try:
            output = subprocess.check_output(cmd_spl)
        except subprocess.CalledProcessError, err:
            self.log.info(
                'Could not get pool stats: %s' % err)
            self.log.exception('Could not get pool stats')
            return []

        return json.loads(output)

    def _publish_stat_sums(self, pool_stats):
        sums = {}
        for pool in pool_stats:
            for path, value in ceph.flatten_dictionary(pool):
                metric = '.'.join(path)
                fval = float(value)
                sums[metric] = (sums[metric] + fval) if metric in sums else fval

        self._publish_stats(self.config['cluster_name'], sums)

    def _publish_stats(self, prefix, stats):
        """
        Given a stats dictionary, publish under the cluster path (respecting
        short_names and cluster_prefix)
        """

        for path, stat_value in ceph.flatten_dictionary(
            stats,
            path=[prefix]
        ):
            stat_name = '.'.join(path)
            self.publish_gauge(stat_name, stat_value)

    def collect(self):
        """
        Collect ceph pool stats
        """
        stats = self._get_stats()

        for pool in stats:
            # remove pool_id and pool_name from the data
            pool_id = pool.pop('pool_id')
            pool_name = pool.pop('pool_name')
            
            self._publish_stats('%s.%d' % (self.config['cluster_name'], pool_id), pool)

        self._publish_stat_sums(stats)

        return
