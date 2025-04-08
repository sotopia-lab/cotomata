import unittest
# Assuming codebase.py is in the same directory or accessible via PYTHONPATH
from codebase import (
    Response, RawStream, SocketError, ConnectionError, ReadTimeoutError,
    ProtocolError, DecodeError, ContentDecodingError, StreamingError
)

class TestFeature1(unittest.TestCase):
    """Tests specific functionality added or modified by Feature 1."""

    def test_socket_error_handling(self):
        """
        Verify that SocketError raised by the raw stream during iteration
        is caught and raised as ConnectionError (Feature 1 specific).
        """
        # Simulate a raw stream that will raise SocketError
        raw_stream = RawStream(data_chunks=[b'data1', b'data2'], error_to_raise=SocketError)
        response = Response(raw_stream_object=raw_stream)

        # Expect ConnectionError when iterating
        with self.assertRaises(ConnectionError) as cm:
            # Consume the iterator to trigger the error
            list(response.iter_content())

        # Check that the original exception was indeed SocketError (optional)
        self.assertIsInstance(cm.exception.__cause__, SocketError)
        print(f"\nTestFeature1: OK - Caught {type(cm.exception).__name__} caused by {type(cm.exception.__cause__).__name__}")

    def test_normal_iteration_still_works(self):
        """Verify that normal iteration works correctly after merge."""
        chunks = [b'hello', b' ', b'world']
        raw_stream = RawStream(data_chunks=chunks, error_to_raise=None)
        response = Response(raw_stream_object=raw_stream)

        # Iterate and collect chunks
        result = list(response.iter_content())
        self.assertEqual(result, chunks)
        # Also test the .content property
        self.assertEqual(response.content, b''.join(chunks))
        print("TestFeature1: OK - Normal iteration successful.")


if __name__ == '__main__':
    unittest.main()