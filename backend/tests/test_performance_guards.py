"""Local guards for query growth and unbounded dashboard payloads."""
import unittest

from sqlalchemy import event

from test_load_control import ControlFlowTest, db, tearDownModule


class Fixture(ControlFlowTest):
    pass


for name in dir(ControlFlowTest):
    if name.startswith('test_'):
        setattr(Fixture, name, None)


class PerformanceGuardTest(Fixture):
    def measured_get(self, path):
        statements = []

        def before_execute(conn, cursor, statement, parameters, context, executemany):
            statements.append(statement)

        event.listen(db.engine, 'before_cursor_execute', before_execute)
        try:
            response = self.client.get(path, headers={'Authorization': 'Bearer ' + self.tokens['admin']})
        finally:
            event.remove(db.engine, 'before_cursor_execute', before_execute)
        self.assertEqual(response.status_code, 200, response.get_data(as_text=True))
        return response, len(statements)

    def test_dashboard_projections_have_bounded_queries_and_payloads(self):
        for name in ('operations', 'productivity', 'quality'):
            response, queries = self.measured_get(
                f'/api/dashboard/{name}?desde=2026-10-15&hasta=2026-10-15')
            self.assertLessEqual(queries, 8, f'{name} ejecutó {queries} consultas')
            self.assertLess(len(response.data), 1_000_000, f'{name} superó 1 MB')

    def test_monitor_has_bounded_queries_and_payload(self):
        response, queries = self.measured_get('/api/load-control/monitor?date=2026-10-15')
        self.assertLessEqual(queries, 20, f'monitor ejecutó {queries} consultas')
        self.assertLess(len(response.data), 1_000_000, 'monitor superó 1 MB')


def load_tests(loader, tests, pattern):
    return loader.loadTestsFromTestCase(PerformanceGuardTest)


if __name__ == '__main__':
    unittest.main()
