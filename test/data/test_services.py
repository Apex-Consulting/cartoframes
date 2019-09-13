# -*- coding: utf-8 -*-
from __future__ import unicode_literals

"""Unit tests for cartoframes.data.services"""
import unittest
import os
import sys
import json
import warnings
import pandas as pd
import logging
import pytest

from carto.exceptions import CartoException

from cartoframes.data import Dataset
from cartoframes.auth import Credentials
from cartoframes.utils.columns import normalize_name


from cartoframes.data.clients import SQLClient


from cartoframes.data.services import Geocode


try:
    import geopandas
    HAS_GEOPANDAS = True
except ImportError:
    HAS_GEOPANDAS = False

from test.helpers import _UserUrlLoader

WILL_SKIP = False
warnings.filterwarnings('ignore')


QUOTAS = {}


def update_quotas(service, quota):
    if not service in QUOTAS:
        QUOTAS[service] = {
            'initial': None,
            'final': None
        }
    QUOTAS[service]['final'] = quota
    if QUOTAS[service]['initial'] is None:
        QUOTAS[service]['initial'] = quota
    return quota


@pytest.fixture(autouse=True, scope='module')
def module_setup_teardown():
    """Run pytest with options --log-level=info --log-cli-level=info
       to see this message about quota used during the tests
    """
    yield
    for service in QUOTAS:
        used_quota = QUOTAS[service]['final'] - QUOTAS[service]['initial']
        logging.info("TOTAL USED QUOTA for %s:  %d", service, used_quota)


class TestGeocode(unittest.TestCase, _UserUrlLoader):
    """Tests for cartoframes.data.service.Geocode"""

    def setUp(self):
        if (os.environ.get('APIKEY') is None or
                os.environ.get('USERNAME') is None):
            try:
                creds = json.loads(open('test/secret.json').read())
                self.apikey = creds['APIKEY']
                self.username = creds['USERNAME']
            except:  # noqa: E722
                warnings.warn("Skipping Context tests. To test it, "
                              "create a `secret.json` file in test/ by "
                              "renaming `secret.json.sample` to `secret.json` "
                              "and updating the credentials to match your "
                              "environment.")
                self.apikey = None
                self.username = None
        else:
            self.apikey = os.environ['APIKEY']
            self.username = os.environ['USERNAME']

        # sets skip value
        WILL_SKIP = self.apikey is None or self.username is None  # noqa: F841

        # table naming info
        has_mpl = 'mpl' if os.environ.get('MPLBACKEND') else 'nonmpl'
        has_gpd = 'gpd' if os.environ.get('USE_GEOPANDAS') else 'nongpd'
        pyver = sys.version[0:3].replace('.', '_')
        buildnum = os.environ.get('TRAVIS_BUILD_NUMBER') or 'none'

        # Skip tests checking quotas when running in TRAVIS
        # since usually multiple tests will be running concurrently
        # in that case
        WILL_SKIP = WILL_SKIP or buildnum != 'none'

        self.test_slug = '{ver}_{num}_{mpl}_{gpd}'.format(
            ver=pyver, num=buildnum, mpl=has_mpl, gpd=has_gpd
        )

        self.test_tables = []

        self.base_url = self.user_url().format(username=self.username)
        self.credentials = Credentials(self.username, self.apikey, self.base_url)
        self.sql_client = SQLClient(self.credentials)

        self.tearDown()

    def get_test_table_name(self, name):
        n = len(self.test_tables) + 1
        table_name = normalize_name(
            'cf_test_table_{name}_{n}_{slug}'.format(name=name, n=n, slug=self.test_slug)
        )
        self.test_tables.append(table_name)
        return table_name

    def tearDown(self):
        """restore to original state"""
        sql_drop = 'DROP TABLE IF EXISTS {};'

        for table in self.test_tables:
            try:
                Dataset(table, credentials=self.credentials).delete()
                self.sql_client.query(sql_drop.format(table))
            except CartoException:
                warnings.warn('Error deleting tables')

    # service: isolines, hires_geocoder
    def used_quota(self, service):
        rows = self.sql_client.query('SELECT * FROM cdb_service_quota_info()')
        for row in rows:
            if row['service'] == service:
                return update_quotas(service, row['used_quota'])
        return None

    @unittest.skipIf(WILL_SKIP, 'no carto credentials, skipping this test')
    def test_geocode_dataframe(self):
        gc = Geocode(credentials=self.credentials)

        df = pd.DataFrame([['Gran Vía 46', 'Madrid'], ['Ebro 1', 'Sevilla']], columns=['address', 'city'])

        quota = self.used_quota('hires_geocoder')

        # Preview
        _, info = gc.geocode(df, street='address', city='city', country="'Spain'", dry_run=True)
        self.assertEqual(info.get('required_quota'), 2)
        self.assertEqual(self.used_quota('hires_geocoder'), quota)

        # Geocode
        gc_df, info = gc.geocode(df, street='address', city='city', country="'Spain'")
        self.assertTrue(isinstance(gc_df, pd.DataFrame))
        self.assertEqual(info.get('required_quota'), 2)
        self.assertEqual(info.get('successfully_geocoded'), 2)
        self.assertEqual(info.get('final_records_with_geometry'), 2)
        quota += 2
        self.assertEqual(self.used_quota('hires_geocoder'), quota)
        self.assertIsNotNone(gc_df.the_geom)

        # Preview, Geocode again (should do nothing)
        _, info = gc.geocode(gc_df, street='address', city='city', country="'Spain'", dry_run=True)
        self.assertEqual(info.get('required_quota'), 0)
        self.assertEqual(self.used_quota('hires_geocoder'), quota)
        _, info = gc.geocode(gc_df, street='address', city='city', country="'Spain'")
        self.assertEqual(info.get('required_quota'), 0)
        self.assertEqual(self.used_quota('hires_geocoder'), quota)

        # Incremental geocoding: modify one row
        gc_df.set_value(1, 'address', 'Gran Via 48')
        _, info = gc.geocode(gc_df, street='address', city='city', country="'Spain'", dry_run=True)
        self.assertEqual(info.get('required_quota'), 1)
        self.assertEqual(self.used_quota('hires_geocoder'), quota)
        _, info = gc.geocode(gc_df, street='address', city='city', country="'Spain'")
        self.assertEqual(info.get('required_quota'), 1)
        quota += 1
        self.assertEqual(self.used_quota('hires_geocoder'), quota)

    @unittest.skipIf(WILL_SKIP, 'no carto credentials, skipping this test')
    def test_geocode_dataframe_as_new_table(self):
        gc = Geocode(credentials=self.credentials)

        df = pd.DataFrame([['Gran Vía 46', 'Madrid'], ['Ebro 1', 'Sevilla']], columns=['address', 'city'])

        quota = self.used_quota('hires_geocoder')

        table_name = self.get_test_table_name('gcdf')

        # Preview
        _, info = gc.geocode(df, street='address', city='city', country="'Spain'", table_name=table_name, dry_run=True)
        self.assertEqual(info.get('required_quota'), 2)
        self.assertEqual(self.used_quota('hires_geocoder'), quota)

        # Geocode
        gc_df, info = gc.geocode(df, street='address', city='city', country="'Spain'", table_name=table_name)
        self.assertTrue(isinstance(gc_df, pd.DataFrame))
        self.assertEqual(info.get('required_quota'), 2)
        self.assertEqual(info.get('successfully_geocoded'), 2)
        self.assertEqual(info.get('final_records_with_geometry'), 2)
        quota += 2
        self.assertEqual(self.used_quota('hires_geocoder'), quota)
        # This could change with provider:
        # self.assertEqual(gc_df.the_geom[1], '0101000020E61000002F34D769A4A50DC0C425C79DD2354440')
        # self.assertEqual(gc_df.the_geom[2], '0101000020E6100000912C6002B7EE17C0C45A7C0A80AD4240')
        self.assertIsNotNone(gc_df.the_geom)
        dataset = Dataset(table_name, credentials=self.credentials)
        dl_df = dataset.download()
        self.assertIsNotNone(dl_df.the_geom)
        self.assertTrue(dl_df.equals(gc_df))

    @unittest.skipIf(WILL_SKIP, 'no carto credentials, skipping this test')
    def test_geocode_table(self):
        gc = Geocode(credentials=self.credentials)

        df = pd.DataFrame([['Gran Vía 46', 'Madrid'], ['Ebro 1', 'Sevilla']], columns=['address', 'city'])
        table_name = self.get_test_table_name('gctb')
        Dataset(df).upload(table_name=table_name, credentials=self.credentials)
        ds = Dataset(table_name, credentials=self.credentials)

        quota = self.used_quota('hires_geocoder')

        # Preview
        _, info = gc.geocode(ds, street='address', city='city', country="'Spain'", dry_run=True)
        self.assertEqual(info.get('required_quota'), 2)
        self.assertEqual(self.used_quota('hires_geocoder'), quota)

        # Geocode
        gc_ds, info = gc.geocode(ds, street='address', city='city', country="'Spain'")
        self.assertTrue(isinstance(gc_ds, Dataset))
        self.assertEqual(info.get('required_quota'), 2)
        self.assertEqual(info.get('successfully_geocoded'), 2)
        self.assertEqual(info.get('final_records_with_geometry'), 2)
        quota += 2
        self.assertEqual(self.used_quota('hires_geocoder'), quota)
        self.assertEqual(gc_ds.table_name, table_name)

        # Preview, Geocode again (should do nothing)
        _, info = gc.geocode(ds, street='address', city='city', country="'Spain'", dry_run=True)
        self.assertEqual(info.get('required_quota'), 0)
        self.assertEqual(self.used_quota('hires_geocoder'), quota)
        _, info = gc.geocode(ds, street='address', city='city', country="'Spain'")
        self.assertEqual(info.get('required_quota'), 0)
        self.assertEqual(self.used_quota('hires_geocoder'), quota)

        # Incremental geocoding: modify one row
        self.sql_client.query("UPDATE {table} SET address='Gran Via 48' WHERE cartodb_id=1".format(table=table_name))
        _, info = gc.geocode(ds, street='address', city='city', country="'Spain'", dry_run=True)
        self.assertEqual(info.get('required_quota'), 1)
        self.assertEqual(self.used_quota('hires_geocoder'), quota)
        _, info = gc.geocode(ds, street='address', city='city', country="'Spain'")
        self.assertEqual(info.get('required_quota'), 1)
        quota += 1
        self.assertEqual(self.used_quota('hires_geocoder'), quota)

    @unittest.skipIf(WILL_SKIP, 'no carto credentials, skipping this test')
    def test_geocode_table_as_new_table(self):
        gc = Geocode(credentials=self.credentials)

        df = pd.DataFrame([['Gran Vía 46', 'Madrid'], ['Ebro 1', 'Sevilla']], columns=['address', 'city'])
        table_name = self.get_test_table_name('gctb')
        Dataset(df).upload(table_name=table_name, credentials=self.credentials)
        ds = Dataset(table_name, credentials=self.credentials)

        new_table_name = self.get_test_table_name('gctb')

        quota = self.used_quota('hires_geocoder')

        # Preview
        _, info = gc.geocode(ds, street='address', city='city', country="'Spain'", table_name=new_table_name, dry_run=True)
        self.assertEqual(info.get('required_quota'), 2)
        self.assertEqual(self.used_quota('hires_geocoder'), quota)

        # Geocode
        gc_ds, info = gc.geocode(ds, street='address', city='city', country="'Spain'", table_name=new_table_name)
        self.assertTrue(isinstance(gc_ds, Dataset))
        self.assertEqual(info.get('required_quota'), 2)
        self.assertEqual(info.get('successfully_geocoded'), 2)
        self.assertEqual(info.get('final_records_with_geometry'), 2)
        quota += 2
        self.assertEqual(self.used_quota('hires_geocoder'), quota)
        self.assertEqual(gc_ds.table_name, new_table_name)

        # Original table should not have been geocoded
        _, info = gc.geocode(ds, street='address', city='city', country="'Spain'", dry_run=True)
        self.assertEqual(info.get('required_quota'), 2)
        self.assertEqual(self.used_quota('hires_geocoder'), quota)

        # Preview, Geocode again (should do nothing)
        _, info = gc.geocode(gc_ds, street='address', city='city', country="'Spain'", dry_run=True)
        self.assertEqual(info.get('required_quota'), 0)
        self.assertEqual(self.used_quota('hires_geocoder'), quota)
        _, info = gc.geocode(gc_ds, street='address', city='city', country="'Spain'")
        self.assertEqual(info.get('required_quota'), 0)
        self.assertEqual(self.used_quota('hires_geocoder'), quota)

    @unittest.skipIf(WILL_SKIP, 'no carto credentials, skipping this test')
    def test_geocode_dataframe_dataset(self):
        gc = Geocode(credentials=self.credentials)

        df = pd.DataFrame([['Gran Vía 46', 'Madrid'], ['Ebro 1', 'Sevilla']], columns=['address', 'city'])
        ds = Dataset(df)

        quota = self.used_quota('hires_geocoder')

        # Preview
        _, info = gc.geocode(ds, street='address', city='city', country="'Spain'", dry_run=True)
        self.assertEqual(info.get('required_quota'), 2)
        self.assertEqual(self.used_quota('hires_geocoder'), quota)

        # Geocode
        gc_ds, info = gc.geocode(ds, street='address', city='city', country="'Spain'")
        self.assertTrue(isinstance(gc_ds, Dataset))
        self.assertEqual(info.get('required_quota'), 2)
        self.assertEqual(info.get('successfully_geocoded'), 2)
        self.assertEqual(info.get('final_records_with_geometry'), 2)
        quota += 2
        self.assertEqual(self.used_quota('hires_geocoder'), quota)
        self.assertIsNotNone(gc_ds.dataframe.the_geom)

    @unittest.skipIf(WILL_SKIP, 'no carto credentials, skipping this test')
    def test_geocode_dataframe_dataset_as_new_table(self):
        gc = Geocode(credentials=self.credentials)

        df = pd.DataFrame([['Gran Vía 46', 'Madrid'], ['Ebro 1', 'Sevilla']], columns=['address', 'city'])
        ds = Dataset(df)

        quota = self.used_quota('hires_geocoder')

        table_name = self.get_test_table_name('gcdfds')

        # Preview
        _, info = gc.geocode(ds, street='address', city='city', country="'Spain'", table_name=table_name, dry_run=True)
        self.assertEqual(info.get('required_quota'), 2)
        self.assertEqual(self.used_quota('hires_geocoder'), quota)

        # Geocode
        gc_ds, info = gc.geocode(ds, street='address', city='city', country="'Spain'", table_name=table_name)
        self.assertTrue(isinstance(gc_ds, Dataset))
        self.assertEqual(info.get('required_quota'), 2)
        self.assertEqual(info.get('successfully_geocoded'), 2)
        self.assertEqual(info.get('final_records_with_geometry'), 2)
        quota += 2
        self.assertEqual(self.used_quota('hires_geocoder'), quota)

    @unittest.skipIf(WILL_SKIP, 'no carto credentials, skipping this test')
    def test_geocode_query(self):
        gc = Geocode(credentials=self.credentials)

        ds = Dataset("SELECT 'Gran Via 46' AS address, 'Madrid' AS city")

        quota = self.used_quota('hires_geocoder')

        # Preview
        _, info = gc.geocode(ds, street='address', city='city', country="'Spain'", dry_run=True)
        self.assertEqual(info.get('required_quota'), 1)
        self.assertEqual(self.used_quota('hires_geocoder'), quota)

        # Geocode
        gc_ds, info = gc.geocode(ds, street='address', city='city', country="'Spain'")
        self.assertTrue(isinstance(gc_ds, Dataset))
        self.assertEqual(info.get('required_quota'), 1)
        self.assertEqual(info.get('successfully_geocoded'), 1)
        self.assertEqual(info.get('final_records_with_geometry'), 1)
        quota += 1
        self.assertEqual(self.used_quota('hires_geocoder'), quota)
        self.assertIsNotNone(gc_ds.dataframe.the_geom)

    @unittest.skipIf(WILL_SKIP, 'no carto credentials, skipping this test')
    def test_geocode_query_as_new_table(self):
        gc = Geocode(credentials=self.credentials)

        ds = Dataset("SELECT 'Gran Via 46' AS address, 'Madrid' AS city")

        quota = self.used_quota('hires_geocoder')

        table_name = self.get_test_table_name('gcdfds')

        # Preview
        _, info = gc.geocode(ds, street='address', city='city', country="'Spain'", table_name=table_name, dry_run=True)
        self.assertEqual(info.get('required_quota'), 1)
        self.assertEqual(self.used_quota('hires_geocoder'), quota)

        # Geocode
        gc_ds, info = gc.geocode(ds, street='address', city='city', country="'Spain'", table_name=table_name)
        self.assertTrue(isinstance(gc_ds, Dataset))
        self.assertEqual(info.get('required_quota'), 1)
        self.assertEqual(info.get('successfully_geocoded'), 1)
        self.assertEqual(info.get('final_records_with_geometry'), 1)
        quota += 1
        self.assertEqual(self.used_quota('hires_geocoder'), quota)

    @unittest.skipIf(WILL_SKIP, 'no carto credentials, skipping this test')
    def test_geocode_dataframe_with_metadata(self):
        gc = Geocode(credentials=self.credentials)

        df = pd.DataFrame([['Gran Vía 46', 'Madrid'], ['Ebro 1', 'Sevilla']], columns=['address', 'city'])

        quota = self.used_quota('hires_geocoder')

        # Preview
        _, info = gc.geocode(df, street='address', city='city', country="'Spain'", metadata='meta', dry_run=True)
        self.assertEqual(info.get('required_quota'), 2)
        self.assertEqual(self.used_quota('hires_geocoder'), quota)

        # Geocode
        gc_df, info = gc.geocode(df, street='address', city='city', country="'Spain'", metadata='meta')
        self.assertTrue(isinstance(gc_df, pd.DataFrame))
        self.assertEqual(info.get('required_quota'), 2)
        self.assertEqual(info.get('successfully_geocoded'), 2)
        self.assertEqual(info.get('final_records_with_geometry'), 2)
        quota += 2
        self.assertEqual(self.used_quota('hires_geocoder'), quota)
        self.assertIsNotNone(gc_df.the_geom)
        self.assertIsNotNone(gc_df.meta)
        self.assertEqual(sorted(gc_df['meta'].apply(json.loads)[1].keys()), ['match_types', 'precision', 'relevance'])

