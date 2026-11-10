"""Supervision alerts are deduplicated, permissioned and auditable."""
import unittest
from urllib.parse import quote

from test_load_control import ControlFlowTest, tearDownModule


class Fixture(ControlFlowTest):
    pass


for name in dir(ControlFlowTest):
    if name.startswith('test_'):
        setattr(Fixture, name, None)


class SupervisionAlertsTest(Fixture):
    def monitor(self, user='admin', expected=200):
        return self.call('get', '/monitor?date=2026-10-15', user, expected)

    def alert_action(self, alert, action, reason='', user='super', expected=200):
        key = quote(alert['key'], safe='')
        return self.call('post', f'/trucks/{alert["truck_id"]}/alerts/{key}/{action}',
                         user, expected, {'reason': reason})

    def test_alert_is_unique_and_can_be_audited(self):
        path = self.start(0, 'picker')
        self.call('post', path + '/pause', 'picker')
        report = self.monitor()
        alerts = [row for row in report['alerts'] if row['type'] == 'proceso_pausado']
        self.assertEqual(len(alerts), 1)
        alert = alerts[0]
        self.alert_action(alert, 'acknowledge')
        current = next(row for row in self.monitor()['alerts'] if row['key'] == alert['key'])
        self.assertEqual(current['status'], 'reconocida')
        self.assertEqual(current['history'][-1]['username'], 'super')
        self.alert_action(current, 'resolve', 'Plan revisado con deposito')
        resolved = next(row for row in self.monitor()['alerts'] if row['key'] == alert['key'])
        self.assertEqual(resolved['status'], 'resuelta')
        self.assertEqual(len(resolved['history']), 2)
        self.assertEqual(self.monitor()['alert_counts']['resuelta'], 1)

    def test_resolve_discard_and_reopen_require_reason(self):
        path = self.start(0, 'picker')
        self.call('post', path + '/pause', 'picker')
        alert = self.monitor()['alerts'][0]
        self.alert_action(alert, 'resolve', 'x', expected=400)
        self.alert_action(alert, 'dismiss', 'No corresponde a la operacion')
        dismissed = next(row for row in self.monitor()['alerts'] if row['key'] == alert['key'])
        self.assertEqual(dismissed['status'], 'descartada')
        self.alert_action(dismissed, 'reopen', '', expected=400)
        self.alert_action(dismissed, 'reopen', 'La condicion debe revisarse otra vez')
        reopened = next(row for row in self.monitor()['alerts'] if row['key'] == alert['key'])
        self.assertEqual(reopened['status'], 'abierta')

    def test_shortage_and_second_control_alerts_do_not_duplicate(self):
        self.complete(1, 'ana', shortage=True)
        first = self.monitor()
        relevant = [row for row in first['alerts'] if row['type'] in
                    ('faltante_pendiente', 'segundo_control_pendiente')]
        self.assertEqual(len(relevant), 2)
        self.assertEqual(len({row['key'] for row in relevant}), 2)
        second = self.monitor()
        self.assertEqual({row['key'] for row in relevant},
                         {row['key'] for row in second['alerts'] if row['type'] in
                          ('faltante_pendiente', 'segundo_control_pendiente')})
        self.complete(2, 'ben', shortage=True)
        types = [row['type'] for row in self.monitor()['alerts']]
        self.assertIn('faltante_pendiente', types)
        self.assertNotIn('segundo_control_pendiente', types)

    def test_paused_process_is_reported_once(self):
        path = self.start(0, 'picker')
        self.call('post', path + '/pause', 'picker')
        alerts = [row for row in self.monitor()['alerts'] if row['type'] == 'proceso_pausado']
        self.assertEqual(len(alerts), 1)
        self.assertEqual(alerts[0]['username'], 'picker')

    def test_permissions_and_unknown_alert(self):
        self.monitor(user='picker', expected=403)
        path = self.start(0, 'picker')
        self.call('post', path + '/pause', 'picker')
        alert = self.monitor()['alerts'][0]
        self.alert_action(alert, 'acknowledge', user='picker', expected=403)
        missing = dict(alert, key='no-existe')
        self.alert_action(missing, 'resolve', 'No existe', expected=404)


def load_tests(loader, tests, pattern):
    return loader.loadTestsFromTestCase(SupervisionAlertsTest)


if __name__ == '__main__':
    unittest.main()
