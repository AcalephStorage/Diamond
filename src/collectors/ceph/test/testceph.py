#!/usr/bin/python
# coding=utf-8

try:
    import json
    json  # workaround for pyflakes issue #13
except ImportError:
    import simplejson as json

import subprocess

from test import CollectorTestCase
from test import get_collector_config
from test import unittest
from test import run_only
from mock import patch, call

from diamond.collector import Collector
import ceph


def run_only_if_assertSequenceEqual_is_available(func):
    pred = lambda: 'assertSequenceEqual' in dir(unittest.TestCase)
    return run_only(func, pred)


class TestCounterIterator(unittest.TestCase):

    @run_only_if_assertSequenceEqual_is_available
    def test_empty(self):
        data = {}
        expected = []
        actual = list(ceph.flatten_dictionary(data))
        self.assertSequenceEqual(actual, expected)

    @run_only_if_assertSequenceEqual_is_available
    def test_simple(self):
        data = {'a': 1, 'b': 2}
        expected = [(['a'], 1), (['b'], 2)]
        actual = list(ceph.flatten_dictionary(data))
        self.assertSequenceEqual(actual, expected)

    @run_only_if_assertSequenceEqual_is_available
    def test_nested(self):
        data = {'a': 1, 'b': 2, 'c': {'d': 3}}
        expected = [(['a'], 1), (['b'], 2), (['c','d'], 3)]
        actual = list(ceph.flatten_dictionary(data))
        self.assertSequenceEqual(actual, expected)

    @run_only_if_assertSequenceEqual_is_available
    def test_doubly_nested(self):
        data = {'a': 1, 'b': 2, 'c': {'d': 3}, 'e': {'f': {'g': 1}}}
        expected = [(['a'], 1), (['b'], 2), (['c', 'd'], 3), (['e', 'f', 'g'], 1)]
        actual = list(ceph.flatten_dictionary(data))
        self.assertSequenceEqual(actual, expected)

    @run_only_if_assertSequenceEqual_is_available
    def test_complex(self):
        data = {"val": 0,
                "max": 524288000,
                "get": 60910,
                "wait": {"avgcount": 0,
                         "sum": 0},
                }
        expected = [
            (['get'], 60910),
            (['max'], 524288000),
            (['val'], 0),
            (['wait', 'avgcount'], 0),
            (['wait', 'sum'], 0),
        ]
        actual = list(ceph.flatten_dictionary(data))
        self.assertSequenceEqual(actual, expected)


class TestCephCollectorSocketNameHandling(CollectorTestCase):

    def setUp(self):
        config = get_collector_config('CephCollector', {
            'interval': 10,
        })
        self.collector = ceph.CephCollector(config, None)

    def test_parse_socket_name(self):
        expected = ('cephadoodle', 'osd', '325')
        sock = '/var/run/ceph/cephadoodle-osd.325.asok'
        actual = self.collector._parse_socket_name(sock)
        self.assertEquals(actual, expected)

    @patch('glob.glob')
    def test_get_socket_paths(self, glob_mock):
        config = get_collector_config('CephCollector', {
            'socket_path': '/path/',
            'socket_ext': 'ext',
        })
        collector = ceph.CephCollector(config, None)

        collector._get_socket_paths()
        glob_mock.assert_called_with('/path/*.ext')


class TestCephCollectorGettingStats(CollectorTestCase):

    def setUp(self):
        config = get_collector_config('CephCollector', {
            'interval': 10,
        })
        self.collector = ceph.CephCollector(config, None)

    def test_import(self):
        self.assertTrue(ceph.CephCollector)

    @patch('ceph._popen_check_output')
    def test_load_works(self, check_output):
        expected = {'a': 1,
                    'b': 2,
        }
        check_output.return_value = (json.dumps(expected), "")
        actual_stats, actual_schema = self.collector._get_perf_counters('a_socket_name')
        self.assertListEqual(check_output.mock_calls,
                             [
                                 call(
                                     [
                                         '/usr/bin/ceph',
                                         '--admin-daemon',
                                         'a_socket_name',
                                         'perf',
                                         'dump',
                                     ]
                                 ),
                                 call(
                                     [
                                         '/usr/bin/ceph',
                                         '--admin-daemon',
                                         'a_socket_name',
                                         'perf',
                                         'schema',
                                     ]
                                 ),
                             ])
        self.assertEqual(actual_stats, expected)
#
#    @run_only_if_subprocess_check_output_is_available
#    @patch('subprocess.check_output')
#    def test_ceph_command_fails(self, check_output):
#        check_output.side_effect = subprocess.CalledProcessError(
#            255, ['/usr/bin/ceph'], 'error!',
#        )
#        actual = self.collector._get_stats_from_socket('a_socket_name')
#        check_output.assert_called_with(['/usr/bin/ceph',
#                                         '--admin-daemon',
#                                         'a_socket_name',
#                                         'perf',
#                                         'dump',
#                                         ])
#        self.assertEqual(actual, {})
#
#    @run_only_if_subprocess_check_output_is_available
#    @patch('json.loads')
#    @patch('subprocess.check_output')
#    def test_json_decode_fails(self, check_output, loads):
#        input = {'a': 1,
#                 'b': 2,
#                 }
#        check_output.return_value = json.dumps(input)
#        loads.side_effect = ValueError('bad data')
#        actual = self.collector._get_stats_from_socket('a_socket_name')
#        check_output.assert_called_with(['/usr/bin/ceph',
#                                         '--admin-daemon',
#                                         'a_socket_name',
#                                         'perf',
#                                         'dump',
#                                         ])
#        loads.assert_called_with(json.dumps(input))
#        self.assertEqual(actual, {})
#
#
#class TestCephCollectorPublish(CollectorTestCase):
#
#    def setUp(self):
#        config = get_collector_config('CephCollector', {
#            'interval': 10,
#        })
#        self.collector = ceph.CephCollector(config, None)
#
#    @patch.object(Collector, 'publish')
#    def test_simple(self, publish_mock):
#        self.collector._publish_stats('prefix', {'a': 1})
#        publish_mock.assert_called_with('prefix.a', 1,
#                                        metric_type='GAUGE', instance=None,
#                                        precision=0)
#
#    @patch.object(Collector, 'publish')
#    def test_multiple(self, publish_mock):
#        self.collector._publish_stats('prefix', {'a': 1, 'b': 2})
#        publish_mock.assert_has_calls([call('prefix.a', 1,
#                                            metric_type='GAUGE', instance=None,
#                                            precision=0),
#                                       call('prefix.b', 2,
#                                            metric_type='GAUGE', instance=None,
#                                            precision=0),
#                                       ])

if __name__ == "__main__":
    unittest.main()
