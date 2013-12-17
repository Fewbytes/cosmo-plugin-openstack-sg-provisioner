#!/usr/bin/env python
# vim: ts=4 sw=4 et

# Standard
import json
import os

# Celery
from celery import task

# OpenStack
import keystoneclient.v2_0.client as ksclient
from novaclient.v1_1 import client

# Cosmo
from cosmo.events import send_event, get_cosmo_properties

@task
def provision(__cloudify_id, nova_config, security_group, **kwargs):
    nova_client = _init_client(nova_config)
    if _get_sg_by_name(nova_client, security_group['name']):
        raise RuntimeError("Can not provision sg with name '{0}' because sg with such name already exists"
                           .format(security_group['name']))

    sg = nova_client.security_groups.create(security_group['name'], security_group.get('description', '(no description)'))
    for rule in security_group['rules']:
        nova_client.security_group_rules.create(
            sg.id,
            ip_protocol="tcp",
            from_port=rule['port'],
            to_port=rule['port'],
            cidr=rule.get('cidr'),
            group_id=rule.get('group_id')
        )
    send_event(__cloudify_id, "cosmo_manager", "sg status", "state", "running") # XXX

@task
def terminate(nova_config, security_group, **kwargs):
    nova_client = _init_client(nova_config)
    sg = _get_sg_by_name(nova_client, security_group['name'])
    nova_client.security_groups.delete(sg.id)


def _init_client(nova_config):
    config_path = os.getenv('KEYSTONE_CONFIG_PATH', os.path.expanduser('~/keystone_config.json'))
    with open(config_path, 'r') as f:
        keystone_config = json.loads(f.read())
    region = nova_config.get('region', keystone_config.get('region', None))
    return client.Client(username=keystone_config['username'],
                         api_key=keystone_config['password'],
                         project_id=keystone_config['tenant_name'],
                         auth_url=keystone_config['auth_url'],
                         region_name=region,
                         http_log_debug=False)


def _get_sg_by_name(nova_client, name):
    # TODO: check whether nova_client can get sgs only named `name`
    sgs = nova_client.security_groups.list()
    matching_sgs = [sg for sg in sgs if sg.name == name]

    if len(matching_sgs) == 0:
        return None
    if len(matching_sgs) == 1:
        return matching_sgs[0]
    raise RuntimeError("Lookup of sg by name failed. There are {0} sgs named '{1}'"
                       .format(len(matching_sgs), name))


def _get_sg_by_name_or_fail(nova_client, name):
    sg = _get_sg_by_name(nova_client, name)
    if sg:
        return sg
    raise ValueError("Lookup of sg by name failed. Could not find a sg with name {0}".format(name))


if __name__ == '__main__':
    nova_client = _init_client()
    json.dumps(nova_client.security_groups.list(), indent=4, sort_keys=True)
