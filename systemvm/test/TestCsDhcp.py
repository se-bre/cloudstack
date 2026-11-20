# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.

import unittest
import mock
from cs.CsDhcp import CsDhcp
from cs import CsHelper
import merge


class TestCsDhcp(unittest.TestCase):

    def setUp(self):
        merge.DataBag.DPATH = "."

    # @mock.patch('cs.CsDhcp.CsHelper')
    # @mock.patch('cs.CsDhcp.CsDnsMasq')
    def test_init(self):
        csdhcp = CsDhcp("dhcpentry", {})
        self.assertTrue(csdhcp is not None)

    def test_merge_keeps_one_entry_per_dns_only_hostname(self):
        import cs_dhcp
        mac = "02:00:00:00:00:01"
        primary = {"mac_address": mac, "ipv4_address": "10.1.1.5", "host_name": "vm1"}
        web = {"mac_address": mac, "ipv4_address": "10.1.1.6", "host_name": "web", "dns_only": True}
        api = {"mac_address": mac, "ipv4_address": "10.1.1.6", "host_name": "api", "dns_only": True}
        dbag = {}
        for entry in (primary, web, api, primary):  # a refreshed primary entry must not evict the hostnames
            dbag = cs_dhcp.merge(dbag, entry)
        self.assertEqual(set(dbag), {"10.1.1.5", "10.1.1.6 web", "10.1.1.6 api"})
        dbag = cs_dhcp.merge(dbag, dict(web, remove=True))
        self.assertTrue(dbag["10.1.1.6 web"]["remove"])
        self.assertFalse(dbag["10.1.1.6 api"].get("remove", False))


if __name__ == '__main__':
    unittest.main()
