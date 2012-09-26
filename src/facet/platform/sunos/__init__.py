import os
import sys
import re
import shlex
import subprocess
import resource

import kstat
import kstat.stats

import facet
import facet.modules
import facet.utils
    
MAX_COUNTER_UINT64 = (2 ** 64) - 1

class SunOSProvider(facet.FacetProvider):

    def __init__(self, **kwargs):
        # Initialize super class
        facet.FacetProvider.__init__(self, **kwargs)
        
        # Initialize Facet modules in this provider
        self._load_provider_modules()
 
    class SunOSLoadAverageModule(facet.modules.LoadAverageModule):

        def __init__(self, **kwargs):
            self._options = kwargs
            self._kstat = kstat.Kstat()

        def get_load_average(self):
            # kstat metric unix:0:system_misc:*
            # NB: load avg values stored a uint32_t and must be scaled by 256 to floating points
            system_misc = self._kstat.retrieve('unix', 0, 'system_misc')
            load_1m = system_misc['avenrun_1min']/256.0
            load_5m = system_misc['avenrun_5min']/256.0
            load_15m = system_misc['avenrun_15min']/256.0
            processes_total = system_misc['nproc']
            processes_running = 0
            return (load_1m, load_5m, load_15m, processes_total, processes_running) 
 
    class SunOSCPUStatModule(facet.modules.CPUStatModule):
        
        _MAX_VALUES = {
            'user': MAX_COUNTER_UINT64, 
            'system': MAX_COUNTER_UINT64, 
            'idle': MAX_COUNTER_UINT64, 
            'iowait': MAX_COUNTER_UINT64 
        }

        def __init__(self, **kwargs):
            self._options = kwargs
            self._kstat = kstat.Kstat()       
 
        def get_cpu_count(self):
            """
            Return the number of cpu's in the system
            """
            # kstat metric: unix:0:system_misc:ncpu 
            system_misc = self._kstat.retrieve('unix', 0, 'system_misc')
            ncpus = system_misc['ncpus'] 
            return ncpus

        def get_cpu_counters(self, cpu=None):
            """
            Return a dict of cpu usage counters 
            """
            usage = {'idle': 0L, 'system':0L, 'user':0L, 'iowait':0L} 
            if cpu:
                return self._get_cpu_counters(cpu)     
            else: 
                for c in range(0, self.get_cpu_count()):
                    cpu_usage = self._get_cpu_counters(c)
                    usage['idle'] += cpu_usage['idle']
                    usage['system'] += cpu_usage['system']
                    usage['user'] += cpu_usage['user']
                    usage['iowait'] += cpu_usage['iowait']
            return usage 

        def _get_cpu_counters(self, cpu):
            # kstat metric: cpu:*:sys
            if cpu < 0 or cpu >= self.get_cpu_count(): 
                raise facet.FacetError("Unknown cpu: %d" % cpu) 
            usage = {}
            kstat_cpu_stat = self._kstat.retrieve('cpu', cpu, 'sys')
            usage['idle'] = kstat_cpu_stat['cpu_ticks_idle']
            usage['system'] = kstat_cpu_stat['cpu_ticks_kernel']
            usage['user'] = kstat_cpu_stat['cpu_ticks_user'] 
            usage['iowait'] = kstat_cpu_stat['cpu_ticks_wait']
            return usage 
        
        def get_cpu_counters_max(self, counter):
            """
            Return the max value for a cpu usage counter
            """
            return self._MAX_VALUES[counter]

    class SunOSMemoryStatModule(facet.modules.MemoryStatModule):

        _SWAP_COMMAND = '/usr/sbin/swap'
        _SWAP_COMMAND_RE = re.compile(r'([A-Za-z0-9/]+)\s(.+)\s([0-9]+)K\s([0-9]+)K\s([0-9]+)K')
 
        def __init__(self, **kwargs):
            self._options = kwargs 
            self._kstat = kstat.Kstat()

        def _get_installed_pages(self):
            self._kstat.update()
            # kstat metric: lgrp:*:*
            installed_pages = 0L
            # Total installed pages can be obtained by summing installed_pages for all locality groups
            for kstat_lgrp in self._kstat.retrieve_all('lgrp', -1, None):
                installed_pages += kstat_lgrp['pages installed']
            return installed_pages

        def get_memory_used(self):
            """
            Return the amount of memory in bytes that is in use 
            """
            self._kstat.update()
            kstat_system_pages = self._kstat.retrieve('unix', -1, 'system_pages')
            total_pages = self._get_installed_pages()
            free_pages = kstat_system_pages['freemem']
            used_pages = total_pages - free_pages 
            return used_pages * resource.getpagesize() 

        def get_memory_total(self):
            """
            Return the amount of memory in bytes is available
            """
            self._kstat.update()
            total_pages = self._get_installed_pages()
            return total_pages * resource.getpagesize() 

        def get_memory_free(self):
            """
            Return the amount of memory in bytes that is not in use
            """
            self._kstat.update()
            kstat_system_pages = self._kstat.retrieve('unix', -1, 'system_pages')
            free_pages = kstat_system_pages['freemem']
            return free_pages * resource.getpagesize() 

        def _run_swap_command(self):
            """
            Execute the swap command and return swaplo, blocks and free
            """
            # Ensure swap command is executable
            if not os.access(self._SWAP_COMMAND, os.X_OK):
                raise FacetError("Unable to execute: %s." % (self._SWAP_COMMAND))

            # Execute swap command
            command = "%s -lk" % (self._SWAP_COMMAND)
            p = subprocess.Popen(shlex.split(command), stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=False)
            (stdout, stderr) = p.communicate()
            if not p or p.returncode != 0:
                raise facet.FacetError("Failed to execute: %s" % command)

            # Parse swap command output
            result = None
            for line in stdout.split('\n'):
                match = self._SWAP_COMMAND_RE.match(line)
                if match:
                    result = (int(match.group(3)), int(match.group(4)), int(match.group(5)))
            return result

        def get_swap_used(self):
            """
            Return the amount of swap in bytes that is in use
            """
            swap_low, swap_total, swap_free = self._run_swap_command()
            return ((swap_total - swap_free) * 1024)
 
        def get_swap_total(self):
            """
            Return the amount of swap in bytes that is available
            """
            swap_low, swap_total, swap_free = self._run_swap_command()
            return (swap_total * 1024) 

        def get_swap_free(self):
            """
            Return the amount of swap in bytes that is not in use
            """
            swap_low, swap_total, swap_free = self._run_swap_command()
            return (swap_free * 1024) 

    class SunOSNetworkStatModule(facet.modules.NetworkStatModule):

        _DRIVERS = ['lo', 'link']

        def __init__(self, **kwargs):
            self._options = kwargs
            self._kstat = kstat.Kstat()

        def _get_kstat_interface(self, interface):
            for drv in self._DRIVERS:
                for kstat_interface in self._kstat.retrieve_all(drv, -1, None):
                    if kstat_interface.data_class == 'net':
                        if kstat_interface.name == interface:
                            return kstat_interface
            raise facet.FacetError("Unknown interface: %s" % (interface))

        def get_interfaces(self):
            """
            Return a list of interfaces present on the system 
            """
            interfaces = []
            for drv in self._DRIVERS:
                for kstat_interface in self._kstat.retrieve_all(drv, -1, None):
                    if kstat_interface.data_class == 'net':
                        interfaces.append(kstat_interface.name)
            return interfaces 

        def get_interface_counters(self, interface):
            """
            Return a dict of network stat counters for the specified interface 
            """
            interface_counters = {}
            
            kstat_interface = self._get_kstat_interface(interface)

            for (counter, value) in kstat_interface.items():
                interface_counters[counter] = long(value)
     
            return interface_counters 

        def get_interface_counters_max(self, counter):
            """
            Return the max value for a network stat counter
            """
            raise NotImplementedError()


    class SunOSDiskStatModule(facet.modules.DiskStatModule):

        _DRIVERS = ['sd', 'dad', 'ssd']

        def __init__(self, **kwargs):
            self._options = kwargs
            self._kstat = kstat.Kstat()
        
        def _get_kstat_disk(self, physical_disk_name):
            """
            Return a kstat object for the given disk     
            """
            for drv in self._DRIVERS:
                for kstat_disk in self._kstat.retrieve_all(drv, -1, None):
                    if kstat_disk.data_class == 'disk':
                        if facet.utils.get_physical_disk_path(kstat_disk.name, drv).split('/')[-1] == physical_disk_name:
                            return kstat_disk 
            raise facet.FacetError("Unknown disk: %s" % (physical_disk_name))

        def get_mounts(self):
            """
            Return a list of mounted filesystems
            """
            return facet.utils.get_mounts() 

        def get_disks(self):
            """
            Return a list of disks
            """
            disks = []
            for drv in self._DRIVERS:
                for kstat_disk in self._kstat.retrieve_all(drv, -1, None):
                    if kstat_disk.data_class == 'disk':
                        physical_disk_name = facet.utils.get_physical_disk_path(kstat_disk.name, drv).split('/')[-1]
                        disks.append(physical_disk_name)
            return disks 
    
        def get_disk_counters(self, physical_disk_name):
            """
            Return a dict of disk stat counters for the specified disk
            """
                       
            """
            typedef struct kstat_io {  
                u_longlong_t nread;       /* number of bytes read */  
                u_longlong_t nwritten;    /* number of bytes written */  
                uint_t       reads;       /* number of read operations */  
                uint_t       writes;      /* number of write operations */  
                hrtime_t wtime;           /* cumulative wait (pre-service) time */  
                hrtime_t wlentime;        /* cumulative wait length*time product*/  
                hrtime_t wlastupdate;     /* last time wait queue changed */  
                hrtime_t rtime;           /* cumulative run (service) time */  
                hrtime_t rlentime;        /* cumulative run length*time product */  
                hrtime_t rlastupdate;     /* last time run queue changed */  
                uint_t wcnt;              /* count of elements in wait state */  
                uint_trcnt;               /* count of elements in run state */  
            } kstat_io_t;
            """
        
            disk_counters = {}
    
            kstat_disk = self._get_kstat_disk(physical_disk_name)

            disk_counters['nread'] = kstat_disk['nwritten']
            disk_counters['nwritten'] = kstat_disk['nread']
            disk_counters['reads'] = kstat_disk['reads']
            disk_counters['writes'] = kstat_disk['writes']
            disk_counters['wtime'] = kstat_disk['wtime']
            disk_counters['wlentime'] = kstat_disk['wlentime'] 
            disk_counters['rtime'] = kstat_disk['rtime']
            disk_counters['rlentime'] = kstat_disk['rlentime']

            return disk_counters 
 
        def get_disk_counters_max(self, counter):
            """
            Return the max value for a disk usage counter
            """
            raise NotImplementedError()

        def get_disk_space_total(self, mount):
            raise NotImplementedError() 

        def get_disk_space_used(self, mount):
            raise NotImplementedError() 

        def get_disk_space_free(self, mount):
            raise NotImplementedError() 