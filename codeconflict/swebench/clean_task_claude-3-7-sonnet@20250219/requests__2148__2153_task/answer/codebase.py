"""
A simplified version of an HTTP client library similar to 'requests'.
This merged implementation includes both socket error handling and
updated exception handling for HTTP protocol errors.
"""
import socket

class Response:
    """Represents an HTTP response."""
    
    def __init__(self):
        self.raw = None
        
    def iter_content(self, chunk_size=1, decode_content=False):
        """
        Iterates over the response data in chunks.
        
        Args:
            chunk_size: Size of chunks to yield
            decode_content: Whether to decode the content
            
        Yields:
            Chunks of response content
            
        Raises:
            ConnectionError: For socket errors or read timeouts
            ContentDecodingError: When content cannot be decoded
            ChunkedEncodingError: When chunked transfer encoding fails
        """
        def generate():
            if self.raw is not None:
                try:
                    # Try to stream from raw response
                    try:
                        for chunk in self.raw.stream(chunk_size, decode_content=decode_content):
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
                    # Standard file-like object fallback
                    while True:
                        chunk = self.raw.read(chunk_size)
                        if not chunk:
                            break
                        yield chunk
            else:
                # No content
                return
                
        # Create and return generator
        return generate()


class RequestException(Exception):
    """Base exception for request errors"""
    pass


class ConnectionError(RequestException):
    """Connection error occurred"""
    pass


class ContentDecodingError(RequestException):
    """Content decoding error occurred"""
    pass


class ChunkedEncodingError(RequestException):
    """Chunked encoding error occurred"""
    pass


# Exceptions that might be raised by the underlying HTTP library
class DecodeError(Exception):
    """Exception raised when decoding fails in the underlying HTTP library"""
    pass


class ProtocolError(Exception):
    """Exception raised when there's an HTTP protocol error"""
    pass


class ReadTimeoutError(Exception):
    """Exception raised when a read operation times out"""
    pass