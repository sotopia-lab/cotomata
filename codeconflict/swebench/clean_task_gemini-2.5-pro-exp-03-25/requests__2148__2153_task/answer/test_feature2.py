import unittest
# Assuming codebase.py is in the same directory or accessible via PYTHONPATH
from codebase import (
    Response, RawStream, SocketError, ConnectionError, ReadTimeoutError,
    ProtocolError, DecodeError, ContentDecodingError, StreamingError
)

class TestFeature2(unittest.TestCase):
    """Tests specific functionality added or modified by Feature 2."""

    def test_read_timeout_error_handling(self):
        """
        Verify that ReadTimeoutError raised by the raw stream is caught
        and raised as ConnectionError (Feature 2 specific).
        """
        # Simulate a raw stream that will raise ReadTimeoutError
        raw_stream = RawStream(data_chunks=[b'chunk1'], error_to_raise=ReadTimeoutError)
        response = Response(raw_stream_object=raw_stream)

        # Expect ConnectionError when iterating
        with self.assertRaises(ConnectionError) as cm:
            list(response.iter_content())

        self.assertIsInstance(cm.exception.__cause__, ReadTimeoutError)
        print(f"\nTestFeature2: OK - Caught {type(cm.exception).__name__} caused by {type(cm.exception.__cause__).__name__}")


    def test_protocol_error_handling(self):
        """
        Verify that ProtocolError raised by the raw stream is caught
        and raised as StreamingError (Feature 2 specific).
        """
        # Simulate a raw stream that will raise ProtocolError
        raw_stream = RawStream(data_chunks=[b'data', b'bits'], error_to_raise=ProtocolError)
        response = Response(raw_stream_object=raw_stream)

        # Expect StreamingError when iterating
        with self.assertRaises(StreamingError) as cm:
            list(response.iter_content())

        self.assertIsInstance(cm.exception.__cause__, ProtocolError)
        print(f"TestFeature2: OK - Caught {type(cm.exception).__name__} caused by {type(cm.exception.__cause__).__name__}")


    def test_base_decode_error_handling_still_works(self):
        """Verify that original DecodeError handling remains functional."""
        raw_stream = RawStream(data_chunks=[b'abc'], error_to_raise=DecodeError)
        response = Response(raw_stream_object=raw_stream)

        with self.assertRaises(ContentDecodingError) as cm:
            list(response.iter_content())

        self.assertIsInstance(cm.exception.__cause__, DecodeError)
        print(f"TestFeature2: OK - Caught {type(cm.exception).__name__} caused by {type(cm.exception.__cause__).__name__}")


if __name__ == '__main__':
    unittest.main()