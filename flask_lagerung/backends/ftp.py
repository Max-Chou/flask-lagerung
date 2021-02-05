import ftplib
import io
import os
from datetime import datetime
from urllib.parse import urljoin, urlparse

from ..utils import filepath_to_uri, DEFAULT_CHUNK_SIZE
from ..base import Storage


class FTPStorage(Storage):
    def __init__(self, location, base_url=None, encoding=None):
        self.location = location
        self.base_url = base_url
        self.encoding = encoding or "utf-8"

        self._config = self._decode_location(location)
        self._connection = None

    def _decode_location(self, location):
        """
        Return configuration from location url.
        """
        splitted_url = urlparse(location)
        config = {}

        if splitted_url.scheme not in ("ftp", "aftp"):
            raise Exception("FTPStorge works only with FTP protocol!")

        if splitted_url.hostname == "":
            raise Exception("You must a least provide hostname!")

        if splitted_url.scheme == "aftp":
            config["active"] = True
        else:
            config["active"] = False

        config["path"] = splitted_url.path
        config["host"] = splitted_url.hostname
        config["user"] = splitted_url.username
        config["password"] = splitted_url.password
        config["port"] = int(splitted_url.port)

        return config

    def _start_connection(self):
        # Check if the connection is still alive and if not, drop it
        if self._connection is not None:
            try:
                self._connection.pwd()
            except ftplib.all_errors:
                self._connection = None

        # make connection
        if self._connection is None:
            ftp = ftplib.FTP()
            ftp.encoding = self.encoding

            try:
                ftp.connect(self._config["host"], self._config["port"])
                ftp.login(self._config["user"], self._config["password"])
                if self._config["active"]:
                    ftp.set_pasv(False)

                if self._config["path"] != "":
                    ftp.cwd(self._config["path"])
                self._connection = ftp
                return
            except ftplib.all_errors:
                raise Exception(
                    "Connection or Login error using data {}".format(repr(self._config))
                )

    def _mkremdirs(self, path):
        pwd = self._connection.pwd()
        path_splitted = path.split(os.path.sep)
        for path_part in path_splitted:
            try:
                self._connection.cwd(path_part)
            except ftplib.all_errors:
                try:
                    self._connection.mkd(path_part)
                    self._connection.cwd(path_part)
                except ftplib.all_errors:
                    raise Exception(f"Cannot create directory chain {path}")
        self._connection.cwd(pwd)

    def _get_dir_details(self, path):
        try:
            lines = []
            self._connection.retrlines("LIST " + path, lines.append)
            dirs = {}
            files = {}
            for line in lines:
                words = line.split()
                if len(words) < 6:
                    continue

                if words[-2] == "->":
                    continue

                if words[0][0] == "d":
                    dirs[words[-1]] = 0
                elif words[0][0] == "-":
                    files[words[-1]] = int(words[-5])

            return dirs, files
        except ftplib.all_errors:
            raise Exception("Error getting listing for {}".format(path))

    def _put_file(self, name, stream):

        try:
            self._mkremdirs(os.path.dirname(name))
            pwd = self._connection.pwd()
            self._connection.cwd(os.path.dirname(name))
            self._connection.storbinary(
                "STOR " + os.path.basename(name), stream, DEFAULT_CHUNK_SIZE
            )
            self._connection.cwd(pwd)
        except ftplib.all_errors:
            raise Exception("Error writing file {}".format(name))

    def _read(self, name):
        memory_file = io.BytesIO()
        try:
            pwd = self._connection.pwd()
            self._connection.cwd(os.path.dirname(name))
            self._connection.retrybinary(
                "RETR " + os.path.basename(name), memory_file.write
            )
            self._connection.cwd(pwd)
            memory_file.seek(0)
            return memory_file
        except ftplib.all_errors:
            raise Exception(f"Error reading file {name}")

    def open(self, name, mode="rb"):
        remote_file = FTPStorageFile(name, self, mode=mode)
        return remote_file

    def disconnect(self):
        self._connection.quit()
        self._connection = None

    def save(self, name, stream):
        self._start_connection()
        self._put_file(name, stream)
        stream.close()
        return name

    def listdir(self, path):
        self._start_connection()

        dirs, files = self._get_dir_details(path)
        return list(dirs.keys()), list(files.keys())

    def delete(self, name):
        if not self.exists(name):
            return

        self._start_connection()
        try:
            self._connection.delete(name)
        except ftplib.all_errors:
            raise Exception("Error when removing {}".format(name))

    def exists(self, name):
        self._start_connection()
        try:
            nlst = self._connection.nlst(os.path.dirname(name) + "/")
            if name in nlst or os.path.basename(name) in nlst:
                return True
            else:
                return False

        except ftplib.error_temp:
            return False

        except ftplib.error_perm:
            # error_perm: 550 Can't find file
            return False

        except ftplib.all_errors:
            raise Exception("Error when testing existence of {}".format(name))

    def url(self, name):
        if self.base_url is None:
            raise ValueError("This file is not accessible via a URL.")

        url = filepath_to_uri(name)
        if url is not None:
            url = url.lstrip("/")

        return urljoin(self.base_url, url)


class FTPStorageFile:
    def __init__(self, name, storage, mode):
        self.name = name
        self.storage = storage
        self.mode = mode
        self.file = io.BytesIO()
        self._is_read = False

    def read(self, num_bytes=None):
        if not self._is_read:
            self.storage._start_connection()
            self.file = self.storage._read(self.name)
            self._is_read = True

        return self.file.read(num_bytes)

    def write(self, stream):
        if "w" not in self.mode:
            raise AttributeError("File was opend for read-only access.")
        self.file = io.BytesIO(stream)
        self._is_read = True

    def close(self):
        self.file.close()
