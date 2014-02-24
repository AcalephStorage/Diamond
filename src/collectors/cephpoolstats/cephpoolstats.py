import subprocess
import re
import os
import sys
import shlex
import json

os.chdir(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, '../ceph')

import ceph


"""
Get ceph pool stats from one node
"""


class CephPoolStatsCollector(ceph.CephCollector):
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
            flat_pool = ceph.flatten_dictionary(pool)

            for metric, value in flat_pool:
                fval = float(value)
                sums[metric] = (sums[metric] + fval) if metric in sums else fval

        self._publish_stats(self.config['cluster_name'], sums)

    def collect(self):
        """
        Collect ceph pool stats
        """
        stats = self._get_stats()
        cluster_name = self.config['cluster_name']

        for pool in stats:
            # remove pool_id and pool_name from the data
            pool_id = pool.pop('pool_id')
            pool_name = pool.pop('pool_name')
            
            self._publish_stats('%s.%s' % (cluster_name, pool_name), pool)

        self._publish_stat_sums(stats)

        return
