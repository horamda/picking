"""Optional device telemetry is minimal, private and never required by picking."""
import json
import os
import unittest
from unittest.mock import patch

from test_load_control import ControlFlowTest, tearDownModule
from models import LogEntry


class Fixture(ControlFlowTest):
    pass


for name in dir(ControlFlowTest):
    if name.startswith('test_'):
        setattr(Fixture, name, None)


class DeviceTelemetryTest(Fixture):
    def event(self, payload, user='picker', expected=201):
        response = self.client.post('/api/load-control/device-events', json=payload,
            headers={'Authorization': 'Bearer ' + self.tokens[user]})
        self.assertEqual(response.status_code, expected, response.get_data(as_text=True))
        return response.json

    def diagnostics(self, query='', user='admin', expected=200):
        response = self.client.get('/api/load-control/device-diagnostics' + query,
            headers={'Authorization': 'Bearer ' + self.tokens[user]})
        self.assertEqual(response.status_code, expected, response.get_data(as_text=True))
        return response.json

    def test_disabled_endpoint_is_non_blocking_and_does_not_write(self):
        with patch.dict(os.environ, {'DEVICE_TELEMETRY_ENABLED': '0'}):
            result = self.event({'event': 'voice_ready', 'platform': 'web'}, expected=202)
        self.assertFalse(result['recorded'])
        self.assertEqual(LogEntry.query.filter_by(entity='device_telemetry').count(), 0)

    def test_enabled_event_stores_only_allowlisted_context(self):
        payload = {'event': 'voice_ready', 'platform': 'android', 'client_version': '1.2.3',
                   'duration_ms': 850, 'transcript': 'dato que no debe persistir',
                   'device_token': 'secreto'}
        with patch.dict(os.environ, {'DEVICE_TELEMETRY_ENABLED': '1'}):
            self.assertTrue(self.event(payload)['recorded'])
            report = self.diagnostics()
        row = LogEntry.query.filter_by(entity='device_telemetry').one()
        details = json.loads(row.details)
        self.assertEqual(details, {'version': 1, 'platform': 'android',
                                   'client_version': '1.2.3', 'duration_ms': 850})
        self.assertEqual(report['counts']['voice_ready'], 1)
        self.assertEqual(report['latency']['voice_ready']['average_ms'], 850)
        self.assertNotIn('transcript', json.dumps(report))
        self.assertNotIn('secreto', json.dumps(report))

    def test_recognition_events_do_not_accept_arbitrary_names_or_errors(self):
        with patch.dict(os.environ, {'DEVICE_TELEMETRY_ENABLED': '1'}):
            self.event({'event': 'audio_upload', 'platform': 'web'}, expected=400)
            self.event({'event': 'voice_activation_failed', 'platform': 'web',
                        'error_code': 'mensaje con espacios'}, expected=400)
            self.event({'event': 'recognition_rejected', 'platform': 'web'})

    def test_diagnostics_permissions_and_range(self):
        self.diagnostics(user='picker', expected=403)
        self.diagnostics('?days=0', expected=400)
        self.diagnostics('?days=texto', expected=400)


def load_tests(loader, tests, pattern):
    return loader.loadTestsFromTestCase(DeviceTelemetryTest)


if __name__ == '__main__':
    unittest.main()
