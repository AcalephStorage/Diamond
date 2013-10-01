#!/usr/bin/python
# coding=utf-8
################################################################################

from test import CollectorTestCase
from test import get_collector_config
from test import unittest
from mock import Mock
from mock import patch


try:
    from cStringIO import StringIO
    StringIO  # workaround for pyflakes issue #13
except ImportError:
    from StringIO import StringIO

from diamond.collector import Collector
from uptime import UptimeCollector

################################################################################

class TestUptimeCollector(CollectorTestCase):
    def setUp(self):
        config = get_collector_config('UptimeCollector', {
                'interval': 10
            })

        self.collector = UptimeCollector(config, None)

    def test_import(self):
        self.assertTrue(UptimeCollector)

    @patch('__builtin__.open')
    @patch('os.access', Mock(return_value=True))
    @patch(Collector, 'publish')
    def test_should_open_proc_uptime(self, publish_mock, open_mock):
        open_mock.return_value = StringIO('')
        self.collector.collect()
        open_mock.assert_called_once_with('/proc/uptime')

    @patch('__builtin__.open')
    def test_should_work_with_synthetic_data(self, publish_mock):
        patch_open = patch('__builtin__.open', Mock(return_value=StringIO('500.0 200.0')))

        patch_open.start()
        self.collector.collect()
        patch_open.stop()

        self.assertPublishedMany(publish_mock, {})

        patch_open = patch('__builtin__.open', Mock(return_value=StringIO('600.0 300.0')))

        patch_open.start()
        self.collector.collect()
        patch_open.stop()

        self.assertPublishedMany(publish_mock, {
            'uptime.up': 600.0, 
            'uptime.idle': 300.0
        })

    @patch(Collector, 'publish')
    def test_should_work_with_real_data(self, publish_mock):
        UptimeCollector.PROC = self.getFixturePath('proc_uptime_1')
        self.collector.collect()

        self.assertPublishedMany(publish_mock, {})

        UptimeCollector.PROC = self.getFixturePath('proc_uptime_1')
        self.collector.collect()

        metrics = {
            'uptime.up': 600.0, 
            'uptime.idle': 300.0
        }

        self.assertPublishedMany(publish_mock, {})        
        
        self.setDocExample(collector=self.collector.__class__.__name__,
                           metrics=metrics,
                           defaultpath=self.collector.config['path'])
        self.assertPublishedMany(publish_mock, metrics)

################################################################################
if __name__ == "__main__":
    unittest.main()