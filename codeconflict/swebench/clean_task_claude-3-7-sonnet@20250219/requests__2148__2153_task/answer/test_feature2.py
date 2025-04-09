"""
Unit tests for Feature 2: Updated Exception Handling for HTTP Protocol Errors
"""
import unittest
from unittest.mock import MagicMock

from codebase import (
    Response, ConnectionError, ContentDecodingError, ChunkedEncodingError,
    DecodeError, ProtocolError, ReadTimeoutError
)


class TestFeature2(unittest.TestCase):
    """Test updated exception handling in Response.iter_content"""
    
    def setUp(self):
        """Set up a Response object for testing"""
        self.response = Response()
    
    def test_protocol_error_is_converted_to_chunked_encoding_error(self):
        """Test that ProtocolError is caught and converted to ChunkedEncodingError"""
        # Create a mock raw object that raises ProtocolError when stream is called
        self.response.raw = MagicMock()
        self.response.raw.stream.side_effect = ProtocolError("Protocol error occurred")
        
        # Verify that a ChunkedEncodingError is raised when iterating over the content
        with self.assertRaises(ChunkedEncodingError):
            list(self.response.iter_content())
        
        # Verify that the stream method was called
        self.response.raw.stream.assert_called_once()
    
    def test_decode_error_is_converted_to_content_decoding_error(self):
        """Test that DecodeError is caught and converted to ContentDecodingError"""
        # Create a mock raw object that raises DecodeError when stream is called
        self.response.raw = MagicMock()
        self.response.raw.stream.side_effect = DecodeError("Decoding error occurred")
        
        # Verify that a ContentDecodingError is raised when iterating over the content
        with self.assertRaises(ContentDecodingError):
            list(self.response.iter_content())
        
        # Verify that the stream method was called
        self.response.raw.stream.assert_called_once()
    
    def test_read_timeout_error_is_converted_to_connection_error(self):
        """Test that ReadTimeoutError is caught and converted to ConnectionError"""
        # Create a mock raw object that raises ReadTimeoutError when stream is called
        self.response.raw = MagicMock()
        self.response.raw.stream.side_effect = ReadTimeoutError("Read timeout occurred")
        
        # Verify that a ConnectionError is raised when iterating over the content
        with self.assertRaises(ConnectionError):
            list(self.response.iter_content())
        
        # Verify that the stream method was called
        self.response.raw.stream.assert_called_once()


if __name__ == '__main__':
    unittest.main()