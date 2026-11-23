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
""" Smoke tests for hostnames on NIC secondary IPs
    (addHostnameToNicSecondaryIp / removeHostnameFromNicSecondaryIp)
"""
import logging

from nose.plugins.attrib import attr
from marvin.cloudstackTestCase import cloudstackTestCase
from marvin.cloudstackAPI import (addIpToNic,
                                  removeIpFromNic,
                                  addHostnameToNicSecondaryIp,
                                  removeHostnameFromNicSecondaryIp,
                                  listNics)
from marvin.lib.utils import get_process_status
from marvin.lib.base import (Account,
                             ServiceOffering,
                             NetworkOffering,
                             Network,
                             VirtualMachine)
from marvin.lib.common import (get_zone,
                               get_domain,
                               get_test_template,
                               list_routers,
                               list_hosts)


class TestNicSecondaryIpHostnames(cloudstackTestCase):

    @classmethod
    def setUpClass(cls):
        cls.logger = logging.getLogger('TestNicSecondaryIpHostnames')
        cls.logger.setLevel(logging.DEBUG)
        cls.logger.addHandler(logging.StreamHandler())

        cls.testClient = super(TestNicSecondaryIpHostnames, cls).getClsTestClient()
        cls.apiclient = cls.testClient.getApiClient()
        cls.services = cls.testClient.getParsedTestDataConfig()
        cls._cleanup = []

        cls.domain = get_domain(cls.apiclient)
        cls.zone = get_zone(cls.apiclient, cls.testClient.getZoneForTests())
        cls.hypervisor = cls.testClient.getHypervisorInfo()
        cls.services['mode'] = cls.zone.networktype
        cls.template = get_test_template(cls.apiclient, cls.zone.id, cls.hypervisor)
        cls.services["virtual_machine"]["zoneid"] = cls.zone.id

        cls.account = Account.create(cls.apiclient, cls.services["account"], admin=True, domainid=cls.domain.id)
        cls._cleanup.append(cls.account)
        cls.service_offering = ServiceOffering.create(cls.apiclient, cls.services["service_offering"])
        cls._cleanup.append(cls.service_offering)
        cls.network_offering = NetworkOffering.create(cls.apiclient, cls.services["isolated_network_offering"],
                                                      conservemode=True)
        cls._cleanup.append(cls.network_offering)
        cls.network_offering.update(cls.apiclient, state='Enabled')
        cls.network = Network.create(cls.apiclient, cls.services["network"],
                                     accountid=cls.account.name,
                                     domainid=cls.account.domainid,
                                     networkofferingid=cls.network_offering.id,
                                     zoneid=cls.zone.id)
        cls._cleanup.append(cls.network)

    @classmethod
    def tearDownClass(cls):
        super(TestNicSecondaryIpHostnames, cls).tearDownClass()

    def setUp(self):
        self.cleanup = []

    def tearDown(self):
        super(TestNicSecondaryIpHostnames, self).tearDown()

    # helpers

    def deploy_vm(self):
        vm = VirtualMachine.create(self.apiclient, self.services["virtual_machine"],
                                   templateid=self.template.id,
                                   accountid=self.account.name,
                                   domainid=self.account.domainid,
                                   serviceofferingid=self.service_offering.id,
                                   networkids=[self.network.id])
        self.cleanup.append(vm)
        return vm

    def add_secondary_ip(self, vm):
        cmd = addIpToNic.addIpToNicCmd()
        cmd.nicid = vm.nic[0].id
        return self.apiclient.addIpToNic(cmd)

    def remove_secondary_ip(self, ip_id):
        cmd = removeIpFromNic.removeIpFromNicCmd()
        cmd.id = ip_id
        self.apiclient.removeIpFromNic(cmd)

    def add_hostname(self, ip_id, hostname):
        cmd = addHostnameToNicSecondaryIp.addHostnameToNicSecondaryIpCmd()
        cmd.id = ip_id
        cmd.hostname = hostname
        return self.apiclient.addHostnameToNicSecondaryIp(cmd)

    def remove_hostname(self, ip_id, hostname):
        cmd = removeHostnameFromNicSecondaryIp.removeHostnameFromNicSecondaryIpCmd()
        cmd.id = ip_id
        cmd.hostname = hostname
        return self.apiclient.removeHostnameFromNicSecondaryIp(cmd)

    def listed_hostnames(self, vm, ip_id):
        """Hostnames of the secondary IP as returned by listNics and listVirtualMachines (asserted equal)"""
        cmd = listNics.listNicsCmd()
        cmd.virtualmachineid = vm.id
        cmd.nicid = vm.nic[0].id
        from_nics = [ip for ip in self.apiclient.listNics(cmd)[0].secondaryip if ip.id == ip_id][0]
        listed_vm = VirtualMachine.list(self.apiclient, id=vm.id)[0]
        from_vms = [ip for ip in listed_vm.nic[0].secondaryip if ip.id == ip_id][0]
        nics_names = sorted(getattr(from_nics, 'hostnames', None) or [])
        vms_names = sorted(getattr(from_vms, 'hostnames', None) or [])
        self.assertEqual(nics_names, vms_names, "listNics and listVirtualMachines disagree on hostnames")
        return nics_names

    def router_hosts_lines(self):
        """/etc/hosts of the network's VR as a list of (ip, name) pairs"""
        router = list_routers(self.apiclient, networkid=self.network.id, listall=True)[0]
        command = "cat /etc/hosts"
        if self.hypervisor.lower() in ('vmware', 'hyperv'):
            result = get_process_status(self.apiclient.connection.mgtSvr, 22,
                                        self.apiclient.connection.user, self.apiclient.connection.passwd,
                                        router.linklocalip, command, hypervisor=self.hypervisor)
        else:
            try:
                host_config = self.config.__dict__["zones"][0].__dict__["pods"][0].__dict__["clusters"][0].__dict__["hosts"][0].__dict__
                host = list_hosts(self.apiclient, id=router.hostid)[0]
                result = get_process_status(host.ipaddress, 22, host_config['username'], host_config['password'],
                                            router.linklocalip, command)
            except KeyError:
                self.skipTest("Provide a marvin config file with host credentials to run %s" % self._testMethodName)
        return [tuple(line.split(None, 1)) for line in result if len(line.split(None, 1)) == 2]

    def assert_router_has(self, ip, name, present=True):
        lines = self.router_hosts_lines()
        self.logger.debug("VR /etc/hosts: %s" % lines)
        self.assertEqual((ip, name) in lines, present,
                         "Expected '%s %s' %s in VR /etc/hosts, got %s" % (ip, name, "present" if present else "absent", lines))

    # tests

    @attr(tags=["advanced", "smoke"], required_hardware="false")
    def test_01_add_remove_hostnames_api(self):
        """Add/remove hostnames on a secondary IP and the checks that guard them

        1. Two hostnames can be added, one per call; they are lowercased and listed by addHostname,
           listNics and listVirtualMachines
        2. Invalid (non RFC 1123) names are refused
        3. A name already on this IP, on another secondary IP, or used as an Instance hostname is refused
        4. Removing a name works; removing one not assigned to this IP is refused
        5. Releasing the secondary IP frees its names for reuse
        """
        vm = self.deploy_vm()
        ip1 = self.add_secondary_ip(vm)
        ip2 = self.add_secondary_ip(vm)

        response = self.add_hostname(ip1.id, "Web")
        self.assertEqual(response.hostnames, ["web"], "hostname must be stored lowercase")
        response = self.add_hostname(ip1.id, "api.example.com")
        self.assertEqual(sorted(response.hostnames), ["api.example.com", "web"])
        self.assertEqual(self.listed_hostnames(vm, ip1.id), ["api.example.com", "web"])

        for bad in ["bad_name", "-web", "web-", "web..example.com", "10.1.1.200", "a" * 64]:
            with self.assertRaises(Exception, msg="hostname %s should be refused" % bad):
                self.add_hostname(ip1.id, bad)

        with self.assertRaises(Exception, msg="duplicate on the same IP should be refused"):
            self.add_hostname(ip1.id, "web")
        with self.assertRaises(Exception, msg="name held by another secondary IP should be refused"):
            self.add_hostname(ip2.id, "web")
        with self.assertRaises(Exception, msg="Instance hostname should be refused"):
            self.add_hostname(ip2.id, vm.name)
        with self.assertRaises(Exception, msg="removing a name of another IP should be refused"):
            self.remove_hostname(ip2.id, "web")

        response = self.remove_hostname(ip1.id, "web")
        self.assertEqual(response.hostnames, ["api.example.com"])
        self.assertEqual(self.listed_hostnames(vm, ip1.id), ["api.example.com"])
        with self.assertRaises(Exception, msg="removing a name that is not assigned should be refused"):
            self.remove_hostname(ip1.id, "web")

        # releasing ip1 deletes its hostnames, so the name can move to ip2
        self.remove_secondary_ip(ip1.id)
        response = self.add_hostname(ip2.id, "api.example.com")
        self.assertEqual(response.hostnames, ["api.example.com"])

    @attr(tags=["advanced", "smoke"], required_hardware="true")
    def test_02_hostnames_on_virtual_router(self):
        """Hostnames are published on the VR as one /etc/hosts line each and follow the VM lifecycle

        1. Each hostname of a secondary IP is its own '<ip> <hostname>' line on the VR
        2. Removing a hostname removes only its line
        3. A network restart with cleanup (new VR) re-creates the lines
        4. Expunging the VM removes the lines
        """
        vm = self.deploy_vm()
        secondary_ip = self.add_secondary_ip(vm)
        ip, ip_id = secondary_ip.ipaddress, secondary_ip.id

        self.add_hostname(ip_id, "web")
        self.add_hostname(ip_id, "api")
        self.assert_router_has(ip, "web")
        self.assert_router_has(ip, "api")
        self.assert_router_has(vm.nic[0].ipaddress, vm.name)  # the primary entry is untouched

        self.remove_hostname(ip_id, "web")
        self.assert_router_has(ip, "web", present=False)
        self.assert_router_has(ip, "api")

        self.network.restart(self.apiclient, cleanup=True)
        self.assert_router_has(ip, "api")

        vm.delete(self.apiclient, expunge=True)
        self.cleanup.remove(vm)
        self.assert_router_has(ip, "api", present=False)
