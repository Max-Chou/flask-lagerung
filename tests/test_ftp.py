import io
from datetime import datetime
from unittest.mock import patch
from unittest import TestCase

from flask_lagerung import FTPStorage, FTPStorageFile

USER = 'foo'
PASSWORD = 'bar'
HOST = 'localhost'
PORT = 21
URL = "ftp://{user}:{password}@{host}:{port}/".format(
    user=USER,
    password=PASSWORD,
    host=HOST,
    port=PORT
)

LIST_FIXTURE = """drwxr-xr-x   2 ftp      nogroup      4096 Jul 27 09:46 dir
-rw-r--r--   1 ftp      nogroup      1024 Jul 27 09:45 fi
-rw-r--r--   1 ftp      nogroup      2048 Jul 27 09:50 fi2"""

def list_retrlines(cmd, func):
    for line in LIST_FIXTURE.splitlines():
        func(line)

class FTPTest(TestCase):
    def setUp(self):
        self.storage = FTPStorage(location=URL)
    
    def test_decode_location(self):
        config = self.storage._decode_location(URL)
        wanted_config = {
            'password': 'bar',
            'host': 'localhost',
            'user': 'foo',
            'active': False,
            'path': '/',
            'port': 21,
        }

        self.assertEqual(config, wanted_config)

        #Test active FTP
        config = self.storage._decode_location('a'+URL)
        wanted_config = {
            'password': 'bar',
            'host': 'localhost',
            'user': 'foo',
            'active': True,
            'path': '/',
            'port': 21,
        }
        self.assertTrue(config, wanted_config)

    def test_decode_location_error(self):
        with self.assertRaises(Exception):
            self.storage._decode_location('foo')
        
        with self.assertRaises(Exception):
            self.storage._decode_location('http://foo.com')

    
    @patch('ftplib.FTP')
    def test_start_connection(self, mock_ftp):
        self.storage._start_connection()
        self.assertIsNotNone(self.storage._connection)
        # start active
        storage = FTPStorage(location='a'+URL)
        storage._start_connection()
        self.assertIsNotNone(storage._connection)

    @patch('ftplib.FTP', **{'return_value.pwd.side_effect': IOError()})
    def test_start_connection_timeout(self, mock_ftp):
        self.storage._start_connection()
        self.assertIsNotNone(self.storage._connection)

    @patch('ftplib.FTP', **{'return_value.connect.side_effect': IOError()})
    def test_start_connection_error(self, mock_ftp):
        with self.assertRaises(Exception):
            self.storage._start_connection()

    @patch('ftplib.FTP', **{'return_value.quit.return_value': None})
    def test_disconnect(self, mock_ftp_quit):
        self.storage._start_connection()
        self.storage.disconnect()
        self.assertIsNone(self.storage._connection)

    @patch('ftplib.FTP', **{'return_value.pwd.return_value': 'foo'})
    def test_mkremdirs(self, mock_ftp):
        self.storage._start_connection()
        self.storage._mkremdirs('foo/bar')

    @patch('ftplib.FTP', **{'return_value.pwd.return_value': 'foo'})
    def test_mkremdirs_n_subdirectories(self, mock_ftp):
        self.storage._start_connection()
        self.storage._mkremdirs('foo/bar/null')

    @patch('ftplib.FTP', **{
        'return_value.pwd.return_value': 'foo',
        'return_value.storbinary.return_value': None
    })
    def test_put_file(self, mock_ftp):
        self.storage._start_connection()
        self.storage._put_file('foo', io.BytesIO(b'foo'))

    @patch('ftplib.FTP', **{
        'return_value.pwd.return_value': 'foo',
        'return_value.storbinary.side_effect': IOError()
    })
    def test_put_file_error(self, mock_ftp):
        self.storage._start_connection()
        with self.assertRaises(Exception):
            self.storage._put_file('foo', io.BytesIO(b'foo'))

    def test_open(self):
        remote_file = self.storage.open('foo')
        self.assertIsInstance(remote_file, FTPStorageFile)

    @patch('ftplib.FTP', **{'return_value.pwd.return_value': 'foo'})
    def test_read(self, mock_ftp):
        self.storage._start_connection()
        self.storage._read('foo')

    @patch('ftplib.FTP', **{'return_value.pwd.side_effect': IOError()})
    def test_read2(self, mock_ftp):
        self.storage._start_connection()
        with self.assertRaises(Exception):
            self.storage._read('foo')

    @patch('ftplib.FTP', **{
        'return_value.pwd.return_value': 'foo',
        'return_value.storbinary.return_value': None
    })
    def test_save(self, mock_ftp):
        self.storage.save('foo', io.BytesIO(b'foo'))

    @patch('ftplib.FTP', **{'return_value.retrlines': list_retrlines})
    def test_listdir(self, mock_retrlines):
        dirs, files = self.storage.listdir('/')
        self.assertEqual(len(dirs), 1)
        self.assertEqual(dirs, ['dir'])
        self.assertEqual(len(files), 2)
        self.assertEqual(sorted(files), sorted(['fi', 'fi2']))

    @patch('ftplib.FTP', **{'return_value.retrlines.side_effect': IOError()})
    def test_listdir_error(self, mock_ftp):
        with self.assertRaises(Exception):
            self.storage.listdir('/')

    @patch('ftplib.FTP', **{'return_value.nlst.return_value': ['foo', 'foo2']})
    def test_exists(self, mock_ftp):
        self.assertTrue(self.storage.exists('foo'))
        self.assertFalse(self.storage.exists('bar'))

    @patch('ftplib.FTP', **{'return_value.nlst.side_effect': IOError()})
    def test_exists_error(self, mock_ftp):
        with self.assertRaises(Exception):
            self.storage.exists('foo')

    @patch('ftplib.FTP', **{
        'return_value.delete.return_value': None,
        'return_value.nlst.return_value': ['foo', 'foo2']
    })
    def test_delete(self, mock_ftp):
        self.storage.delete('foo')
        self.assertTrue(mock_ftp.return_value.delete.called)

    def test_url(self):
        with self.assertRaises(ValueError):
            self.storage._base_url = None
            self.storage.url('foo')
        self.storage = FTPStorage(location=URL, base_url='http://foo.bar/')
        self.assertEqual('http://foo.bar/foo', self.storage.url('foo'))
