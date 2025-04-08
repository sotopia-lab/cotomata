"""
A simplified HTTP client library similar to requests, focusing on response handling.
"""

import socket
import collections
from io import BytesIO
from urllib3.exceptions import DecodeError, ReadTimeoutError, ProtocolError

class RequestException(Exception):
    """Base exception class for all request-related exceptions."""
    pass

class HTTPError(RequestException):
    """Exception raised for HTTP error responses."""
    pass

class ConnectionError(RequestException):
    """Exception raised for connection-related errors."""
    pass

class ChunkedEncodingError(RequestException):
    """Exception raised when a chunked transfer encoding fails."""
    pass

class ContentDecodingError(RequestException):
    """Exception raised when content decoding fails."""
    pass

class Response:
    """HTTP Response object containing status, headers, and body content."""
    
    def __init__(self):
        self.status_code = 200
        self.headers = {}
        self.raw = None
        self.encoding = None
        self._content = False
        
    @property
    def content(self):
        """Returns the content of the response as bytes."""
        if self._content is False:
            if self.raw is None:
                self._content = b''
            else:
                self._content = b''.join(self.iter_content(chunk_size=1024)) or b''
        return self._content
    
    def iter_content(self, chunk_size=1, decode_unicode=False):
        """
        Iterates over the response content in chunks.
        
        This method can be used for streaming large responses without
        loading the entire content into memory at once.
        
        Args:
            chunk_size: Size of chunks to yield
            decode_unicode: Whether to decode the content to Unicode
            
        Yields:
            Chunks of content as bytes or str (if decode_unicode is True)
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
            else:
                # Standard file-like object.
                while True:
                    chunk = self.raw.read(chunk_size)
                    if not chunk:
                        break
                    yield chunk
                    
        for chunk in generate():
            if decode_unicode and chunk:
                # Decode the chunk to Unicode if requested
                if self.encoding:
                    chunk = chunk.decode(self.encoding, errors='replace')
                else:
                    chunk = chunk.decode('utf-8', errors='replace')
            yield chunk
            
    def __iter__(self):
        """Allows iterating directly over the response content in lines."""
        return self.iter_lines()
    
    def iter_lines(self, chunk_size=512, decode_unicode=False):
        """Iterates over the response content line by line."""
        pending = None
        
        for chunk in self.iter_content(chunk_size=chunk_size, decode_unicode=decode_unicode):
            if pending is not None:
                chunk = pending + chunk
                
            lines = chunk.splitlines()
            
            if lines and lines[-1] and chunk and lines[-1][-1] == chunk[-1]:
                pending = lines.pop()
            else:
                pending = None
                
            for line in lines:
                yield line
                
        if pending is not None:
            yield pending