import importlib.util
from pathlib import Path
import unittest
import uuid

ROOT=Path(__file__).resolve().parent.parent


def module(name, file):
    spec=importlib.util.spec_from_file_location(name, ROOT/file)
    value=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


client=module('client_profile', 'client/generate_profile.py')
server=module('server_config', 'server/render_config.py')


class Templates(unittest.TestCase):
    def setUp(self):
        self.info={'server':'100.64.0.10','port':10808,'uuid':str(uuid.uuid4())}
        self.cfg=client.build_profile(self.info,'C:/Mihomo/home/tailscale-state')

    def test_visible_group(self):
        self.assertEqual(self.cfg['proxy-groups'][0]['name'],'SERVER')

    def test_provider_preserves_chain(self):
        for proxy in self.cfg['proxies']:
            proxy.pop('dialer-proxy', None)
        node=self.cfg['proxy-providers']['private-egress']['payload'][0]
        self.assertEqual(node['dialer-proxy'],'TAILNET')

    def test_no_embedded_exit_node_dependency(self):
        self.assertNotIn('exit-node',self.cfg['proxies'][0])

    def test_rules_and_dns(self):
        self.assertIn('GEOSITE,cn,DIRECT',self.cfg['rules'])
        self.assertEqual(self.cfg['rules'][-1],'MATCH,SERVER')
        self.assertIn('#SERVER',self.cfg['dns']['nameserver'][0])

    def test_no_automatic_system_capture(self):
        self.assertFalse(self.cfg['tun']['enable'])
        self.assertFalse(self.cfg['allow-lan'])

    def test_public_listener_rejected(self):
        with self.assertRaises(ValueError): server.render('0.0.0.0',self.info['uuid'])

    def test_public_server_rejected(self):
        self.info['server']='203.0.113.10'
        with self.assertRaises(ValueError): client.build_profile(self.info,'C:/Mihomo/state')

    def test_nil_identity_rejected(self):
        self.info['uuid']=str(uuid.UUID(int=0))
        with self.assertRaises(ValueError): client.build_profile(self.info,'C:/Mihomo/state')

    def test_relative_state_rejected(self):
        with self.assertRaises(ValueError): client.build_profile(self.info,'relative-state')

    def test_private_server_scope(self):
        value=server.render(self.info['server'],self.info['uuid'])
        self.assertEqual(value['inbounds'][0]['listen'],self.info['server'])
        self.assertEqual(value['inbounds'][0]['streamSettings']['security'],'none')
        self.assertIn('100.64.0.0/10',value['routing']['rules'][0]['ip'])


if __name__=='__main__': unittest.main()
