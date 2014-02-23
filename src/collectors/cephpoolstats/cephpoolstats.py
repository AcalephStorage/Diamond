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
            return {}

        return json.loads(output)

    def collect(self):
        """
        Collect ceph pool stats
        """
        stats = self._get_stats()

        for pool in stats:
            pool_id = pool.pop('pool_id')
            pool_name = pool.pop('pool_name')
            self._publish_stats('cephpoolstats.%s' % pool_name, pool)

        return
