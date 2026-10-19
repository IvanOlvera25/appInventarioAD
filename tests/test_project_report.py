import unittest
from datetime import date
from decimal import Decimal
from unittest.mock import Mock

from project_report import read_project_report


class ResultCursor:
    def __init__(self, sets):
        self.sets = sets
        self.index = 0
        self.closed = False
        self.executed = None

    @property
    def description(self):
        current = self.sets[self.index]
        return [(key,) for key in current[0]] if current is not None else None

    def execute(self, sql, parameters):
        self.executed = (sql, parameters)

    def fetchall(self):
        return self.sets[self.index][1]

    def nextset(self):
        self.index += 1
        return self.index < len(self.sets)

    def close(self):
        self.closed = True


class ProjectReportTests(unittest.TestCase):
    def read(self, sets, fp='9895'):
        cursor = ResultCursor(sets)
        connection = Mock()
        connection.cursor.return_value = cursor
        engine = Mock()
        engine.raw_connection.return_value = connection
        return engine, connection, cursor

    def test_real_deliveries_and_same_material_in_different_areas(self):
        columns = ['area', 'material_id', 'name', 'category', 'unit',
                   'quantity_requested', 'quantity_delivered', 'quantity_pending']
        engine, connection, cursor = self.read([
            (['id', 'status', 'created_at'], [(1, 'completada', date(2026, 10, 19))]),
            (columns, [('Impresión', 893, 'Tela Foler Stretch', 'Telas', 'm', Decimal('12'), Decimal('12'), Decimal('0')),
                       ('Metal', 864, 'Tubo', 'Metal', 'pza', 8, 9, -1),
                       ('Costura', 893, 'Tela Foler Stretch', 'Telas', 'm', 3, 0, 3)]),
            None,
        ])
        report = read_project_report(engine, '9895')
        self.assertEqual(report['requests'][0]['status'], 'completada')
        self.assertEqual(report['requests'][0]['created_at'], '2026-10-19')
        self.assertEqual(len(report['materials']), 3)
        self.assertEqual(report['materials'][1]['quantity_delivered'], 12)
        self.assertEqual(report['materials'][1]['quantity_pending'], 0)
        self.assertEqual(report['materials'][2]['quantity_pending'], -1)
        self.assertTrue(cursor.closed)
        self.assertEqual(cursor.index, 3)
        connection.rollback.assert_called_once()
        connection.close.assert_called_once()

    def test_empty_results_and_parameterized_fp(self):
        engine, _, cursor = self.read([(['id'], []), (['area'], []), None])
        fp = "x'); DROP TABLE project; --"
        self.assertEqual(read_project_report(engine, fp), {'requests': [], 'materials': []})
        self.assertEqual(cursor.executed, ('CALL sp_resumen_fp(%s)', (fp,)))

    def test_invalid_procedure_result_does_not_silently_show_empty_report(self):
        engine, connection, cursor = self.read([(['id'], []), None])
        with self.assertRaises(ValueError):
            read_project_report(engine, '9895')
        self.assertTrue(cursor.closed)
        connection.close.assert_called_once()

    def test_database_failure_releases_connection(self):
        engine, connection, cursor = self.read([])
        cursor.execute = Mock(side_effect=RuntimeError('database unavailable'))
        with self.assertRaises(RuntimeError):
            read_project_report(engine, '9895')
        self.assertTrue(cursor.closed)
        connection.rollback.assert_called_once()
        connection.close.assert_called_once()


if __name__ == '__main__':
    unittest.main()
