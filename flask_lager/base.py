import os
from datetime import datetime
from urllib.parse import urljoin

from werkzeug.datastructures import FileStorage


class Storage:
    def open(self, name):
        pass

    def save(self, name, fileObj):
        pass

    def path(self, name):
        pass

    def delete(self, name):
        pass
    
    def exists(self, name):
        pass
    
    def listdir(self, path):
        pass

    def url(self, name):
        pass


class FileSystemStorage(Storage):
    def __init__(self, location, base_url=None):
        self.location = os.path.abspath(location)
        self.base_url = base_url
    
    def open(self, name, mode='rb'):
        return FileStorage(stream=open(self.path(name), mode))

    def path(self, name):
        return os.path.join(self.location, name)

    def exists(self, name):
        return os.path.exists(self.path(name))

    def save(self, name, fileObj):
        if not isinstance(fileObj, FileStorage):
            raise TypeError("fileObj must be a werkzeug.FileStorage")
        
        full_path = self.path(name)

        # create any intermediate directories that do not exist.
        directory = os.path.dirname(full_path)
        if not os.path.exists(directory):
            # there's a race between os.path.exists() and os.makedirs()...
            os.makedirs(directory)
        
        if not os.path.isdir(directory):
            raise IOError("{} exists and is not a directory.".format(directory))
        
        # save the file by FileStorage save methods...
        fileObj.save(full_path)

    def listdir(self, path):
        path = self.path(path)
        directories, files = [], []
        for entry in os.scandir(path):
            if entry.is_dir():
                directories.append(entry.name)
            else:
                files.append(entry.name)
        return directories, files

    def url(self, name):
        if self.base_url is None:
            raise ValueError('This file is not accessible via a URL.')

        return urljoin(self.base_url, name)

    def delete(self, name):
        
        name = self.path(name)

        try:
            if os.path.isdir(name):
                os.rmdir(name)
            else:
                os.remove(name)
        except FileNotFoundError:
            pass
