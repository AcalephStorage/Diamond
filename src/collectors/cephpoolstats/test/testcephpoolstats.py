#!/usr/bin/python
# coding=utf-8

try:
    import json
    json  # workaround for pyflakes issue #13
except ImportError:
    import simplejson as json

import shlex
import subprocess

from test import CollectorTestCase
from test import get_collector_config
from test import unittest
from test import run_only
from mock import patch, call

from diamond.collector import Collector
import cephpoolstats


def run_only_if_subprocess_check_output_is_available(func):
    pred = lambda: 'check_output' in dir(subprocess)
    return run_only(func, pred)

class TestCephCollectorGettingStats(CollectorTestCase):

    def setUp(self):
        config = get_collector_config('CephPoolStatsCollector', {
            'interval': 10,
        })
        self.collector = cephpoolstats.CephPoolStatsCollector(config, None)

    def test_import(self):
        self.assertTrue(cephpoolstats.CephPoolStatsCollector)

    @run_only_if_subprocess_check_output_is_available
    @patch('subprocess.check_output')
    def test_load_works(self, check_output):
        cmd = "%s --cluster=%s osd pool stats --format=json" % (
                        self.collector.config['ceph_binary'], 
                        self.collector.config['cluster_name'] )
        cmd_spl = shlex.split(cmd)

        expected = [{'pool_id': 1,
                    'pool_name': 'sample_pool',
                    'recovery': {}, 
                    'recovery_rate': {}, 
                    'client_io_rate': {}
                    }]
        check_output.return_value = json.dumps(expected)
        actual = self.collector._get_stats()
        check_output.assert_called_with(cmd_spl)
        self.assertEqual(actual, expected)

    @run_only_if_subprocess_check_output_is_available
    @patch('subprocess.check_output')
    def test_ceph_command_fails(self, check_output):
        cmd = "%s --cluster=%s osd pool stats --format=json" % (
                        self.collector.config['ceph_binary'], 
                        self.collector.config['cluster_name'] )
        cmd_spl = shlex.split(cmd)

        check_output.side_effect = subprocess.CalledProcessError(
            255, ['/usr/bin/ceph'], 'error!',
        )
        actual = self.collector._get_stats()
        check_output.assert_called_with(cmd_spl)
        self.assertEqual(actual, [])

if __name__ == "__main__":
    unittest.main()
