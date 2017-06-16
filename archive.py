"""
Archive messages compress with lzma to HCP using boto.
"""

# pylint: disable=too-few-public-methods,too-many-arguments

import base64
import hashlib
import io
import json


from backports import lzma
from boto.s3.connection import S3Connection


# HCP #facepalm
import ssl
if hasattr(ssl, '_create_unverified_context'):
    ssl._create_default_https_context = ssl._create_unverified_context


class Archive(object):
    """Save content lzma compressed at default level to object store through boto."""

    def __init__(self, aws_id, aws_secret, server, bucket, object_prefix=""):
        aws_id = base64.b64encode(aws_id)
        aws_secret = hashlib.md5(aws_secret).hexdigest()
        hs3 = S3Connection(aws_access_key_id=aws_id,
                           aws_secret_access_key=aws_secret,
                           host=server)
        self.bucket = hs3.get_bucket(bucket)
        self.object_prefix = object_prefix

        if len(object_prefix) > 0 and not object_prefix.endswith("/"):
            self.object_prefix += "/"

    def save(self, archive_name, content):
        """Save content as a lzma compressed object in object store."""
        # prefix/archive_name
        obj_name = "%s%s" % (self.object_prefix, archive_name)

        buffer_bytes = io.BytesIO()
        with lzma.open(buffer_bytes, mode="wt") as compressor:
            compressor.write(json.dumps(content).decode())
        self.bucket.new_key(obj_name).set_contents_from_string(buffer_bytes.getvalue())
