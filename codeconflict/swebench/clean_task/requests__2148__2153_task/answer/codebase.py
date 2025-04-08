"""
A simplified version of a HTTP request handling library, similar to requests.
This example focuses on the Response class and how it processes streaming content.
"""

import collections
import socket
from io import BytesIO

class RequestException(Exception):
    """Base exception for all request-related errors"""
    pass

class HTTPError(RequestException):
    """Raised when an HTTP error occurs"""
    pass

class ConnectionError(RequestException):
    """Raised when a connection error occurs"""
    pass

class ChunkedEncodingError(RequestException):
    """Raised when an encoding error occurs in chunked transfer"""
    pass

class ContentDecodingError(RequestException):
    """Raised when a content decoding error occurs"""
    pass

class DecodeError(Exception):
    """Exception raised by urllib3 when decoding fails"""
    pass

class ProtocolError(Exception):
    """Exception raised by urllib3 for protocol errors"""
    pass

class ReadTimeoutError(Exception):
    """Exception raised by urllib3 for read timeouts"""
    pass

class Response:
    """
    An HTTP Response object that handles the result of an HTTP request.
    """
    def __init__(self):
        self.raw = None
        self.content = b''
        self.encoding = None
        self.status_code = 200
        self.reason = "OK"
        self.headers = {}
    
    def iter_content(self, chunk_size=1, decode_unicode=False):
        """
        Iterates over the response data. This avoids reading the content
        at once into memory for large responses.
        
        :param chunk_size: Number of bytes to read into memory at once.
        :param decode_unicode: If True, content will be decoded using the response
                               encoding and returned as text.
        """
        def generate():
            if hasattr(self.raw, 'stream'):
                try:
                    for chunk in self.raw.stream(chunk_size, decode_content=True):
                        yield chunk
                except ProtocolError as e:
                    raise ChunkedEncodingError(e)
                except DecodeError as e:
                    raise ContentDecodingError(e)
                except ReadTimeoutError as e:
                    raise ConnectionError(e)
                except socket.error as e:
                    raise ConnectionError(e)
            except AttributeError:
                # Standard file-like object.
                while True:
                    chunk = self.raw.read(chunk_size)
                    if not chunk:
                        break
                    yield chunk
        
        chunks = generate()
        
        if decode_unicode:
            for chunk in chunks:
                yield chunk.decode(self.encoding or 'utf-8')
        else:
            for chunk in chunks:
                yield chunk