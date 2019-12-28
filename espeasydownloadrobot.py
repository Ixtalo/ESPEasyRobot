#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""espeasydownloadrobot.py - Automatically download ESPEasy config files.

Manually downloading the configuration of a couple of ESPEasy instances
can be tedious. This script automates this process.
First, it asks for a dnsmasqd leases file to collect the IP addresses
of ESP instances.
Then it continuously probes for awake ESP instances.
Then it downloads all files with HTTP GET.

ESPEasy Web UI: https://www.letscontrolit.com/wiki/index.php?title=ESP_Easy_web_interface

Usage:
  espeasydownloadrobot.py [--verbose] <config.json>
  espeasydownloadrobot.py -h | --help
  espeasydownloadrobot.py --version

Arguments:
  <config.json>   JSON configuration file.

Options:
  --verbose       Be more verbosive (debugging statements).
  -h --help       Show this screen.
  --version       Show version.
"""
import json
import logging
##
## LICENSE:
##
## Copyright (C) 2019 Alexander Streicher
##
## This program is free software: you can redistribute it and/or modify
## it under the terms of the GNU Affero General Public License as published by
## the Free Software Foundation, either version 3 of the License, or
## (at your option) any later version.
##
## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU Affero General Public License for more details.
##
## You should have received a copy of the GNU Affero General Public License
## along with this program.  If not, see <http://www.gnu.org/licenses/>.
##
import os
import re
import sys
import time
import zipfile
from codecs import open

import requests
from docopt import docopt

__version__ = "1.0"
__date__ = "2019-12-27"
__updated__ = "2019-12-28"
__author__ = "Ixtalo"
__license__ = "AGPL-3.0+"
__email__ = "ixtalo@gmail.com"
__status__ = "Production"


## ESPEasy downloadable files
DOWNLOAD_FILES = ('json', 'config.dat', 'security.dat', 'rules1.txt', 'rules2.txt',
                  'rules3.txt', 'rules4.txt', 'esp.css', 'notification.dat')
DEBUG = 0
TESTRUN = 0
PROFILE = 0
__script_dir = os.path.dirname(os.path.realpath(__file__))

## check for Python3
if sys.version_info < (3, 0):
    sys.stderr.write("Minimum required version is Python 3.x!\n")
    sys.exit(1)


#def create_cache(cache_filename):
#    logging.debug("Creating cache ...")
#    cache = {
#        'timestamp': time.time(),
#        'ips_hostnames': get_ips_from_leases_live()
#    }
#    logging.debug("Storing cache to %s", cache_filename)
#    with open(cache_filename, 'wb') as cache_fout:
#        pickle.dump(cache, cache_fout)
#    return cache


def get_ips_from_leases_live(uri_leases):
    regex_dnsmasq_leases = re.compile("^[0-9]{10} [a-f0-9:]{17} ([0-9.]{7,15}) ([^ ]+) \\*$")
    ## dnsmasq.leases
    req = requests.get(uri_leases)
    ips_hostnames = []
    if req.ok:
        for line in req.iter_lines(decode_unicode=True):
            m = regex_dnsmasq_leases.match(line)
            ip, hostname = m.groups()
            if hostname.startswith('ESP-'):
                ips_hostnames.append((ip, hostname))
    return ips_hostnames


def main():
    arguments = docopt(__doc__, version=f"EspEasyDownloadRobot {__version__} ({__updated__})")
    #print(arguments)

    ## config filename
    config_filename = arguments['<config.json>']
    if not os.path.isabs(config_filename):
        ## assume path local to this very script's path, if not already absolute
        config_filename = os.path.join(__script_dir, config_filename)
    config_filename = os.path.abspath(config_filename)
    logging.info("Config file: %s", config_filename)

    ## setup logging
    logging.basicConfig(level=logging.DEBUG if arguments['--verbose'] else logging.INFO)
    logging.getLogger('urllib3.connectionpool').setLevel(logging.WARNING)

    ## load configuration
    with open(config_filename) as cfgf:
        config = json.load(cfgf)

    ### cache
    #cache_filename = f"{os.path.splitext(sys.argv[0])[0]}.cache"
    #if not os.path.exists(cache_filename):
    #    cache = create_cache(cache_filename)
    #else:
    #    with open(cache_filename, 'rb') as cache_fin:
    #        cache = pickle.load(cache_fin)
    #        cache_ts = cache.get('timestamp', 0)
    #        logging.debug("Cache timestamp: %d (%s)", cache_ts, time.ctime(cache_ts))
    #        if abs(cache_ts - time.time()) > 7200:
    #            logging.warning("Cache too old - recreating ...")
    #            cache = create_cache(cache_filename)

    ## get leases data
    ips_hostnames = get_ips_from_leases_live(config['uri_leases'])
    logging.info("%d candidates found from leases data", len(ips_hostnames))

    ## continuous probing for awake ESP nodes
    todo = [ip for ip, _ in ips_hostnames]
    ip2hostname = dict(ips_hostnames)
    while len(todo) > 0:
        for ip in todo:
            archive_filename = "%s_%s.zip" % (ip.replace('.', '-'), ip2hostname[ip])
            if os.path.exists(archive_filename):
                logging.warning("Skipping %s, already done.", archive_filename)
                todo.remove(ip)
                continue

            logging.info("Processing %s, %s", ip, ip2hostname[ip])

            ## check if alive with HTTP HEAD
            try:
                url = f"http://{ip}/json"
                r = requests.head(url, timeout=1, proxies=config['proxies'])
                if not r.ok:
                    logging.warning("%s is not an ESPEasy node! (no /json)", ip)
                    todo.remove(ip)
                    continue
            except requests.exceptions.ConnectTimeout:
                continue

            ## download data directly to ZIP file
            with zipfile.ZipFile(archive_filename, 'a', compression=zipfile.ZIP_DEFLATED) as zf:

                ## https://www.letscontrolit.com/wiki/index.php?title=ESP_Easy_web_interface#The_hardcode_way
                for filename in DOWNLOAD_FILES:
                    url = f"http://{ip}/{filename}"
                    r = requests.get(url, proxies=config['proxies'], auth=tuple(config['auth']))
                    logging.debug("%s: %s", url, r.ok)

                    zf.writestr(filename, r.content)

            ## this IP is done, remove it from to do list
            todo.remove(ip)

        time.sleep(15)

    return 0


if __name__ == "__main__":
    if DEBUG:
        sys.argv.append("--verbose")
    if TESTRUN:
        import doctest
        doctest.testmod()
    if PROFILE:
        import cProfile
        import pstats
        profile_filename = __file__+'.profile.bin'
        cProfile.run('main()', profile_filename)
        with open("%s.txt" % profile_filename, "wb") as statsfp:
            p = pstats.Stats(profile_filename, stream=statsfp)
            stats = p.strip_dirs().sort_stats('cumulative')
            stats.print_stats()
        sys.exit(0)
    sys.exit(main())

