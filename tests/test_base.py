import os
import shutil
import sys
import tempfile
import unittest

from flask_lager import FileSystemStorage


class FileStorageTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.storage = FileSystemStorage(location=self.temp_dir, base_url='/test_media_url/')
    
    def tearDown(self):
        shutil.rmtree(self.temp_dir)
    
    def test_empty_location(self):

        storage = FileSystemStorage(location='')
        self.assertEqual(storage.location, os.getcwd())

    def test_file_access_options(self):
        self.assertFalse(self.storage.exists('storage_test'))
        f = self.storage.open('storage_test', 'w')
        f.stream.write('storage contents')
        f.stream.close()
        self.assertTrue(self.storage.exists('storage_test'))

        f = self.storage.open('storage_test', 'r')
        self.assertEqual(f.stream.read(), 'storage contents')
        f.stream.close()

        self.storage.delete('storage_test')
        self.assertFalse(self.storage.exists('storage_test'))

    def test_file_path(self):
        pass

    def test_file_url(self):
        pass

    def test_listdir(self):
        pass
