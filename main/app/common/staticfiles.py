"""Normalize browser URL separators for prefixed static folders on Windows."""
import os

from django.contrib.staticfiles.finders import FileSystemFinder


class PortableFileSystemFinder(FileSystemFinder):
    def find_location(self, root, path, prefix=None):
        # Django compares prefix + os.sep before safe_join; URL paths use '/'.
        return super().find_location(root, path.replace('/', os.sep), prefix)
