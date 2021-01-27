import os
import io
import shutil
import sys
import tempfile
import unittest

from flask_lagerung import FileSystemStorage


class FileStorageTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.storage = FileSystemStorage(location=self.temp_dir, base_url='/test_media_url/')
    
    def tearDown(self):
        shutil.rmtree(self.temp_dir)
    
    def test_empty_location(self):
        """
        Make sure the empty location is the current location where you execute the tests.
        """
        storage = FileSystemStorage(location='')
        self.assertEqual(storage.location, os.getcwd())

    def test_file_access_options(self):
        """
        Standard file access options are available, and work as expected.
        """
        self.assertFalse(self.storage.exists('storage_test'))
        f = self.storage.open('storage_test', 'w')
        f.write('storage contents')
        f.close()
        self.assertTrue(self.storage.exists('storage_test'))

        f = self.storage.open('storage_test', 'r')
        self.assertEqual(f.read(), 'storage contents')
        f.close()

        self.storage.delete('storage_test')
        self.assertFalse(self.storage.exists('storage_test'))

    def test_file_save(self):
        """
        File storage can save the file object.
        """
        content = io.StringIO("storage contents")
        self.storage.save("storage_test", content)
        self.assertTrue(self.storage.exists('storage_test'))

        f = self.storage.open('storage_test', 'r')
        self.assertEqual(f.read(), 'storage contents')

    def test_file_save_with_path(self):
        """
        Save a pathname should create intermediate directories as necessary.
        """
        self.assertFalse(self.storage.exists('path/to'))
        self.storage.save('path/to/test.file', io.BytesIO(b'file saved with path'))

        self.assertTrue(self.storage.exists('path/to'))
        with self.storage.open('path/to/test.file') as f:
            self.assertTrue(f.read(), b'file saved with path')
        
        self.assertTrue(os.path.exists(os.path.join(self.temp_dir, 'path', 'to', 'test.file')))

        self.storage.delete('path/to/test.file')


    def test_file_path(self):
        """
        File storage returns the full path of file.
        """
        self.assertFalse(self.storage.exists('test.file'))

        f = io.StringIO("custom content")
        f_name = self.storage.save('test.file', f)
        self.assertEqual(self.storage.path(f_name), os.path.join(self.temp_dir, f_name))

        self.storage.delete(f_name)

    def test_file_url(self):
        """
        File storage returns the url to access the given file from web.
        """
        self.assertEqual(self.storage.url('test.file'), self.storage.base_url + 'test.file')

        self.assertEqual(
            self.storage.url(r"~!*()'@#$%^&*abc`+ =.file"),
            "/test_media_url/~!*()'%40%23%24%25%5E%26*abc%60%2B%20%3D.file"
        )
        self.assertEqual(self.storage.url("ab\0c"), "/test_media_url/ab%00c")

         # should translate os path separator(s) to the url path separator
        self.assertEqual(self.storage.url("""a/b\\c.file"""), "/test_media_url/a/b/c.file")

        # #25905: remove leading slashes from file names to prevent unsafe url output
        self.assertEqual(self.storage.url("/evil.com"), "/test_media_url/evil.com")
        self.assertEqual(self.storage.url(r"\evil.com"), "/test_media_url/evil.com")
        self.assertEqual(self.storage.url("///evil.com"), "/test_media_url/evil.com")
        self.assertEqual(self.storage.url(r"\\\evil.com"), "/test_media_url/evil.com")

        self.assertEqual(self.storage.url(None), "/test_media_url/")

    def test_listdir(self):
        self.assertFalse(self.storage.exists('storage_test_1'))
        self.assertFalse(self.storage.exists('storage_test_2'))
        self.assertFalse(self.storage.exists('storage_dir_1'))

        self.storage.save('storage_test_1', io.StringIO('custom content'))
        self.storage.save('storage_test_2', io.StringIO('custom content'))
        os.mkdir(os.path.join(self.temp_dir, 'storage_dir_1'))

        dirs, files = self.storage.listdir('')
        self.assertEqual(set(dirs), {'storage_dir_1'})
        self.assertEqual(set(files), {'storage_test_1', 'storage_test_2'})

        self.storage.delete('storage_test_1')
        self.storage.delete('storage_test_2')
        os.rmdir(os.path.join(self.temp_dir, 'storage_dir_1'))

    def test_base_url(self):
        self.storage.base_url = None
        with self.assertRaises(ValueError):
            self.storage.url('test.file')
        
        storage = FileSystemStorage(location=self.temp_dir, base_url='/no_ending_slash')
        self.assertEqual(storage.url('test.file'), "{}{}".format(storage.base_url, 'test.file'))
