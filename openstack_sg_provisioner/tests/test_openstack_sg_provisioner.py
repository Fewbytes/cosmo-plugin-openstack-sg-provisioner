#!/usr/bin/env python
# vim: ts=4 sw=4 et

import logging
import random
import string
import unittest

import openstack_sg_provisioner.tasks as tasks

RANDOM_LEN = 3  # cosmo_test_nova_XXX_something

PORT = 65000
CIDR = '1.2.3.0/24'

class OpenstackSGProvisionerTestCase(unittest.TestCase):

    def setUp(self):
        logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        self.logger = logging.getLogger("test_openstack_sg_provisioner")
        self.logger.level = logging.DEBUG
        self.logger.info("setUp called")
        self.nova_client = tasks._init_client({})
        self.name_prefix = 'cosmo_test_nova_{0}_'.format(''.join(
            [random.choice(string.ascii_uppercase + string.digits) for i in range(RANDOM_LEN)]
        ))

    def tearDown(self):
        # CLI all tests cleanup:
        for sg in self.nova_client.security_groups.list():
            if sg.name.startswith(self.name_prefix):
                self.logger.error("Cleaning up security group {0} (id {1})".format(sg.name, sg.id))
                self.nova_client.security_groups.delete(sg.id)

    def test_all(self):

        name = self.name_prefix + 'sg1'
        sg_data = {
            'name': name,
            'description': 'description for ' + name,
            'rules': [
                {'port': PORT, 'cidr': CIDR},
            ]
        }

        tasks.provision(name, {}, sg_data)
        sg = tasks._get_sg_by_name(self.nova_client, name)
        self.assertIsNotNone(sg)
        # print(dir(sg.rules), sg.rules)
        self.assertEquals(sg.rules[0]['from_port'], PORT)
        self.assertEquals(sg.rules[0]['to_port'], PORT)
        self.assertEquals(sg.rules[0]['ip_range']['cidr'], CIDR)

        tasks.terminate({}, sg_data)
        sg = tasks._get_sg_by_name(self.nova_client, name)
        self.assertIsNone(sg)


if __name__ == '__main__':
    unittest.main()
