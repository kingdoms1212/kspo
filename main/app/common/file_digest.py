"""Streaming content identity shared by CSV publisher and readers."""
import hashlib


def sha256_file(path):
    with open(path, 'rb') as source:
        return hashlib.file_digest(source, 'sha256').hexdigest()
