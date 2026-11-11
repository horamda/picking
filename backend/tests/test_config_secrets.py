"""Los secretos por defecto no pueden usarse en Railway."""
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault('DATABASE_URL', 'sqlite:///:memory:')
os.environ.setdefault('ALLOW_SQLITE_FOR_TESTS', '1')
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import config

RAILWAY = {'RAILWAY_ENVIRONMENT': 'production'}
LOCAL = {'RAILWAY_ENVIRONMENT': '', 'RAILWAY_PROJECT_ID': '', 'RAILWAY_SERVICE_ID': ''}


class SecretPolicyTest(unittest.TestCase):
    def test_railway_rejects_missing_default_or_short_secret(self):
        for value in ('', 'jwtsecret', 'supersecret', 'replace_with_jwt_secret', 'corto'):
            with patch.dict(os.environ, dict(RAILWAY, JWT_SECRET=value)):
                with self.assertRaises(RuntimeError):
                    config.get_secret('JWT_SECRET', 'jwtsecret')

    def test_railway_accepts_own_long_secret(self):
        secret = 'x' * 32
        with patch.dict(os.environ, dict(RAILWAY, JWT_SECRET=secret)):
            self.assertEqual(config.get_secret('JWT_SECRET', 'jwtsecret'), secret)

    def test_local_keeps_development_default(self):
        with patch.dict(os.environ, dict(LOCAL, JWT_SECRET='')):
            self.assertEqual(config.get_secret('JWT_SECRET', 'jwtsecret'), 'jwtsecret')


if __name__ == '__main__':
    unittest.main()
