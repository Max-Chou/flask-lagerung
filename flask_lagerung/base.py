import os
import io
from datetime import datetime
from urllib.parse import urljoin
from shutil import copyfileobj

from .utils import filepath_to_uri, create_chunks





class Storage:
    """
    A base storage class, providing some default methods all other storage
    systems can inherit or override.
    """
    def open(self, name):
        """Open the specified file from storage."""
        raise NotImplementedError('subclasses of Storage must provide a open() method')

    def save(self, name, content):
        """Save new content to the file specified by name."""
        raise NotImplementedError('subclasses of Storage must provide a save() method')

    def path(self, name):
        """Return a local filesystem path where the file can be retrieved."""
        pass

    def delete(self, name):
        """Delete the specified file from the storage system."""
        raise NotImplementedError('subclasses of Storage must provide a delete() method')
    
    def exists(self, name):
        """Return True if a file exists in the storage system."""
        raise NotImplementedError('subclasses of Storage must provide a exists() method')
    
    def listdir(self, path):
        """List the contents of the specified path."""
        raise NotImplementedError('subclasses of Storage must provide a listdir() method')

    def url(self, name):
        """Return an absolute URL where the file can be accessed by a client."""
        pass


class FileSystemStorage(Storage):
    """
    Standard local filesystem storage
    """
    def __init__(self, location='', base_url=None):
        self.location = os.path.abspath(location)
        if base_url is not None and not base_url.endswith('/'):
            base_url += '/'
        self.base_url = base_url
        
    
    def open(self, name, mode='rb'):
        return open(self.path(name), mode)

    def path(self, name):
        return os.path.join(self.location, name)

    def exists(self, name):
        return os.path.exists(self.path(name))

    def save(self, name, stream):
        if isinstance(stream, io.StringIO):
            mode = 'w'
        elif isinstance(stream, io.BytesIO):
            mode = 'wb'
        else:
            raise TypeError("stream must be io.StringIO or io.BytesIO object")
        
        full_path = self.path(name)

        # create any intermediate directories that do not exist.
        directory = os.path.dirname(full_path)
        if not os.path.exists(directory):
            # there's a race between os.path.exists() and os.makedirs()...
            os.makedirs(directory)
        
        if not os.path.isdir(directory):
            raise IOError("{} exists and is not a directory.".format(directory))

        
        # if the uploaded file is too large, it can overwhelm the system!
        # Therefore, I have to make the chunks of the uploaded files.
        chunks = create_chunks(stream)
        with open(full_path, mode) as f:
            for chunk in chunks:
                f.write(chunk)
        
        return name


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

        url = filepath_to_uri(name)
        if url is not None:
            url = url.lstrip('/')

        return urljoin(self.base_url, url)

    def delete(self, name):
        name = self.path(name)
        try:
            if os.path.isdir(name):
                os.rmdir(name)
            else:
                os.remove(name)
        except FileNotFoundError:
            pass
