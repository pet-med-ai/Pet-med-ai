"""Complete old payloads, documents, KPI and business data around new GETs."""
import os
import unittest
from unittest.mock import patch
from test_clinical_followup_contact_isolation import ContactIsolation
from test_clinical_followup_contact_overview import FIXTURE, PARAMS, FLAGS


class ContactOverviewIsolation(ContactIsolation):
    # Reuse fixture utilities, not its test suite, to make new assertions independent.
    def test_old_payloads_docs_records_and_business_unchanged_across_new_reads(self):
        with patch.dict(os.environ, FLAGS):
            for species in ('dog', 'cat'):
                if species == 'cat':
                    self.change_case(species='cat', patient_name='CW-B20 合成猫')
                    self.source = self.save_plan('correct', self.source, FIXTURE['plan'])
                row = self.contact_save(data=FIXTURE['contact'])
                for operation in ('read', 'correct', 'withdraw'):
                    if operation != 'read': row = self.contact_save(operation, row, FIXTURE['corrected'])
                    original = self.snapshots(); contacts = self.contact(); business = self.all_business()
                    legacy10 = self.client.get(self.overview_url, headers=self.owner_headers).json(); legacy10.pop('read_at')
                    for _ in range(2):
                        response = self.client.get(self.overview_url, headers=self.owner_headers, params=PARAMS)
                        self.assertEqual(response.status_code, 200, response.text)
                        self.assertEqual(response.json()['groups']['contacts']['records'], contacts['records'])
                    self.assertEqual(self.snapshots(), original); self.assertEqual(self.contact(), contacts)
                    self.assertEqual(self.all_business(), business)
                    again = self.client.get(self.overview_url, headers=self.owner_headers).json(); again.pop('read_at')
                    self.assertEqual(again, legacy10)


if __name__ == '__main__':
    suite = unittest.TestSuite([ContactOverviewIsolation('test_old_payloads_docs_records_and_business_unchanged_across_new_reads')])
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    raise SystemExit(not result.wasSuccessful())
