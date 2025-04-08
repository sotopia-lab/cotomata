"""
Tests for the Response class and its iter_content method to ensure
both features are working correctly.
"""

import pytest
import socket
from codebase import Response, ConnectionError, ChunkedEncodingError, ContentDecodingError, DecodeError, ProtocolError, ReadTimeoutError

class TestResponse:
    
    def test_iter_content_basic_functionality(self):
        """Test the basic functionality of iter_content"""
        r = Response()
        
        class MockRaw:
            def stream(self, chunk_size, decode_content=None):
                yield b'chunk1'
                yield b'chunk2'
        
        r.raw = MockRaw()
        content = b''.join(r.iter_content())
        assert content == b'chunk1chunk2'
    
    def test_iter_content_decode_unicode(self):
        """Test that iter_content correctly decodes unicode"""
        r = Response()
        r.encoding = 'utf-8'
        
        class MockRaw:
            def stream(self, chunk_size, decode_content=None):
                yield 'hello'.encode('utf-8')
                yield 'world'.encode('utf-8')
        
        r.raw = MockRaw()
        content = ''.join(r.iter_content(decode_unicode=True))
        assert content == 'helloworld'
    
    def test_iter_content_handles_socket_error(self):
        """Test that iter_content correctly catches and wraps socket errors"""
        r = Response()
        
        class MockRaw:
            def stream(self, chunk_size, decode_content=None):
                raise socket.error("Socket connection broken")
        
        r.raw = MockRaw()
        with pytest.raises(ConnectionError):
            list(r.iter_content())
    
    def test_iter_content_handles_protocol_error(self):
        """Test that iter_content correctly catches and wraps ProtocolError"""
        r = Response()
        
        class MockRaw:
            def stream(self, chunk_size, decode_content=None):
                raise ProtocolError("Protocol error occurred")
        
        r.raw = MockRaw()
        with pytest.raises(ChunkedEncodingError):
            list(r.iter_content())
    
    def test_iter_content_handles_decode_error(self):
        """Test that iter_content correctly catches and wraps DecodeError"""
        r = Response()
        
        class MockRaw:
            def stream(self, chunk_size, decode_content=None):
                raise DecodeError("Decode error occurred")
        
        r.raw = MockRaw()
        with pytest.raises(ContentDecodingError):
            list(r.iter_content())
    
    def test_iter_content_handles_read_timeout_error(self):
        """Test that iter_content correctly catches and wraps ReadTimeoutError"""
        r = Response()
        
        class MockRaw:
            def stream(self, chunk_size, decode_content=None):
                raise ReadTimeoutError("Read timeout occurred")
        
        r.raw = MockRaw()
        with pytest.raises(ConnectionError):
            list(r.iter_content())
    
    def test_file_like_object_handling(self):
        """Test that iter_content handles file-like objects correctly"""
        r = Response()
        
        class MockRaw:
            def __init__(self):
                self.data = [b'chunk1', b'chunk2', b'']
                self.index = 0
                
            def read(self, size):
                chunk = self.data[self.index]
                self.index += 1
                return chunk
        
        r.raw = MockRaw()
        content = b''.join(r.iter_content())
        assert content == b'chunk1chunk2'