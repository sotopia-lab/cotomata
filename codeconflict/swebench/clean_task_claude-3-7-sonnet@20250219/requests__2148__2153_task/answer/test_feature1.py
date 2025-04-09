"""
Unit tests for Feature 1: Socket Error Handling in Response Streaming
"""
import unittest
import socket
from unittest.mock import MagicMock

from codebase import Response, ConnectionError


class TestFeature1(unittest.TestCase):
    """Test socket error handling in Response.iter_content"""
    
    def setUp(self):
        """Set up a Response object for testing"""
        self.response = Response()
        
    def test_socket_error_is_converted_to_connection_error(self):
        """Test that socket.error is caught and converted to ConnectionError"""
        # Create a mock raw object that raises socket.error when stream is called
        self.response.raw = MagicMock()
        self.response.raw.stream.side_effect = socket.error("Connection reset by peer")
        
        # Verify that a ConnectionError is raised when iterating over the content
        with self.assertRaises(ConnectionError):
            list(self.response.iter_content())
        
        # Verify that the stream method was called
        self.response.raw.stream.assert_called_once()
    
    def test_regular_streaming_works(self):
        """Test that normal streaming still works after our changes"""
        # Create a mock raw object that returns a list of chunks
        expected_chunks = [b'chunk1', b'chunk2', b'chunk3']
        self.response.raw = MagicMock()
        self.response.raw.stream.return_value = expected_chunks
        
        # Iterate over the content and verify the chunks
        actual_chunks = list(self.response.iter_content())
        self.assertEqual(actual_chunks, expected_chunks)
        
        # Verify that the stream method was called
        self.response.raw.stream.assert_called_once()


if __name__ == '__main__':
    unittest.main()