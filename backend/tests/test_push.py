"""Isolated DB fixtures; Firebase sends are mocked and production is never used."""
from test_load_control import ControlFlowTest, application, db, tearDownModule
from services.push import PushDevice, available_tasks, utcnow, retry_delay
from push_worker import process_device
from models import User
from services.load_control import ControlTruck
from unittest.mock import patch, Mock
import unittest


class PushTest(ControlFlowTest):
    # Share fixtures without repeating the parent suite.
    pass


for name in list(dir(ControlFlowTest)):
    if name.startswith('test_'):
        setattr(PushTest, name, None)


class PushDeviceTest(PushTest):
    def test_disabled_and_registration_ownership(self):
        token = 'fake-token-for-isolated-test-only'
        with patch.dict('os.environ', {'PUSH_ENABLED': '0'}):
            self.call('post', '/push/device', 'picker', data={'token': token}, expected=503)
        with patch.dict('os.environ', {'PUSH_ENABLED': '1'}):
            self.call('post', '/push/device', 'picker', data={'token': 'bad'}, expected=400)
            self.call('post', '/push/device', 'picker', data={'token': token})
            self.call('post', '/push/device', 'picker', data={'token': token})
            self.assertEqual(PushDevice.query.count(), 1)
            self.call('delete', '/push/device', 'pallet', data={'token': token})
            self.assertEqual(PushDevice.query.count(), 1)
            self.call('post', '/push/device', 'pallet', data={'token': token})
            self.assertEqual(PushDevice.query.one().user_id, User.query.filter_by(username='pallet').one().id)
            self.call('delete', '/push/device', 'picker', data={'token': token})
            self.assertEqual(PushDevice.query.count(), 1)
            self.call('delete', '/push/device', 'pallet', data={'token': token})
            self.assertEqual(PushDevice.query.count(), 0)

    def test_queue_approval_and_reservation(self):
        self.select_dispatch({self.source.id})
        user = User.query.filter_by(username='picker').one()
        trucks = ControlTruck.query.all()
        self.assertEqual(available_tasks(user, trucks), [])
        self.approve_dispatch()
        tasks = available_tasks(user, ControlTruck.query.all())
        self.assertEqual(tasks, [f'{self.load_id}:1:0'])
        self.call('post', f'/loads/{self.load_id}/courts/1/start/0', 'admin')
        self.assertEqual(available_tasks(user, ControlTruck.query.all()), [])

    def test_sender_retries_and_suppresses_repeated_task_sets(self):
        device = PushDevice(token='fake', known_tasks=[], failures=0)
        sender = Mock()
        self.assertTrue(process_device(device, ['1:1:0'], sender))
        self.assertTrue(process_device(device, ['1:1:0'], sender))
        self.assertEqual(sender.call_count, 1)
        sender.side_effect = TimeoutError()
        self.assertFalse(process_device(device, ['2:1:0'], sender))
        self.assertEqual(device.known_tasks, ['1:1:0'])
        self.assertGreater(device.next_attempt, utcnow())
        self.assertEqual(device.failures, 1)
        self.assertEqual(retry_delay(100), 3600)
        sender.side_effect = None
        self.assertTrue(process_device(device, ['2:1:0'], sender))
        self.assertEqual(device.failures, 0)


def load_tests(loader, tests, pattern):
    return loader.loadTestsFromTestCase(PushDeviceTest)


if __name__ == '__main__':
    unittest.main()
