import unittest
import socket
from unittest.mock import MagicMock, patch
from codebase import Response, ConnectionError

class TestSocketErrorHandling(unittest.TestCase):
    
    def test_iter_content_handles_socket_error(self):
        """Test that socket.error exceptions are wrapped in ConnectionError."""
        response = Response()
        
        # Create a mock raw object that raises socket.error when streamed
        mock_raw = MagicMock()
        mock_raw.stream.side_effect = socket.error("Connection reset by peer")
        
        response.raw = mock_raw
        
        # Attempt to iterate through the content, which should raise ConnectionError
        with self.assertRaises(ConnectionError):
            list(response.iter_content())
        
        # Verify that the stream method was called with expected parameters
        mock_raw.stream.assert_called_once_with(1, decode_content=True)
    
    def test_socket_error_properly_wrapped(self):
        """Test that the original socket error is preserved in the ConnectionError."""
        response = Response()
        original_error = socket.error("DNS resolution failed")
        
        # Create a mock raw object that raises socket.error when streamed
        mock_raw = MagicMock()
        mock_raw.stream.side_effect = original_error
        
        response.raw = mock_raw
        
        # Catch the ConnectionError and verify it contains the original error
        try:
            list(response.iter_content())
            self.fail("ConnectionError was not raised")
        except ConnectionError as e:
            self.assertEqual(e.args[0], original_error)

if __name__ == "__main__":
    unittest.main()