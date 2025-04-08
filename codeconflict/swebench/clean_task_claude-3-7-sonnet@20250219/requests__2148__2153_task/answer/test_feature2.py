import unittest
from unittest.mock import MagicMock
import urllib3.exceptions
from codebase import Response, ConnectionError, ChunkedEncodingError, ContentDecodingError

class TestUrllib3ExceptionHandling(unittest.TestCase):
    
    def test_protocol_error_handling(self):
        """Test that ProtocolError is caught and wrapped as ChunkedEncodingError."""
        response = Response()
        
        # Create a mock raw object that raises ProtocolError when streamed
        mock_raw = MagicMock()
        original_error = urllib3.exceptions.ProtocolError("Chunked transfer encoding failed")
        mock_raw.stream.side_effect = original_error
        
        response.raw = mock_raw
        
        # Verify ChunkedEncodingError is raised with the original exception
        with self.assertRaises(ChunkedEncodingError) as context:
            list(response.iter_content())
            
        self.assertEqual(context.exception.args[0], original_error)
    
    def test_decode_error_handling(self):
        """Test that DecodeError is caught and wrapped as ContentDecodingError."""
        response = Response()
        
        # Create a mock raw object that raises DecodeError when streamed
        mock_raw = MagicMock()
        original_error = urllib3.exceptions.DecodeError("Content decoding failed")
        mock_raw.stream.side_effect = original_error
        
        response.raw = mock_raw
        
        # Verify ContentDecodingError is raised with the original exception
        with self.assertRaises(ContentDecodingError) as context:
            list(response.iter_content())
            
        self.assertEqual(context.exception.args[0], original_error)
    
    def test_read_timeout_error_handling(self):
        """Test that ReadTimeoutError is caught and wrapped as ConnectionError."""
        response = Response()
        
        # Create a mock raw object that raises ReadTimeoutError when streamed
        mock_raw = MagicMock()
        original_error = urllib3.exceptions.ReadTimeoutError(None, None, "Read timed out")
        mock_raw.stream.side_effect = original_error
        
        response.raw = mock_raw
        
        # Verify ConnectionError is raised with the original exception
        with self.assertRaises(ConnectionError) as context:
            list(response.iter_content())
            
        self.assertEqual(context.exception.args[0], original_error)

if __name__ == "__main__":
    unittest.main()