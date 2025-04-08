# Simplified base exception classes
class CustomBaseException(Exception):
    """Base for our custom exceptions."""
    pass

class ConnectionError(CustomBaseException):
    """Simulates a connection-related error."""
    pass

class ContentDecodingError(CustomBaseException):
    """Simulates an error during content decoding."""
    pass

# Simplified simulation of lower-level exceptions
class DecodeError(CustomBaseException):
    """Simulates an error from a lower-level decoding process."""
    pass

class SocketError(OSError): # Inheriting from OSError like socket.error often does
    """Simulates a low-level socket error."""
    pass

class ReadTimeoutError(CustomBaseException):
     """Simulates a read timeout error from an underlying library."""
     pass

class ProtocolError(CustomBaseException):
     """Simulates a protocol error from an underlying library."""
     pass

# --- Core Logic ---

class RawStream:
    """Simulates the raw stream object (like urllib3's response)."""
    def __init__(self, data_chunks=None, error_to_raise=None):
        self._chunks = data_chunks if data_chunks else [b'chunk1', b'chunk2']
        self._error_to_raise = error_to_raise
        self._iterator = iter(self._chunks)

    def stream(self, chunk_size=1, decode_content=False):
        """Simulates streaming data, potentially raising an error."""
        # Simplified: ignores chunk_size and decode_content for this example
        try:
            while True:
                if self._error_to_raise:
                    # Raise the error *before* yielding the last chunk
                    if len(self._chunks) <= 1 :
                         raise self._error_to_raise("Simulated stream error")
                yield next(self._iterator)
                if self._error_to_raise:
                     # Keep track of yielded chunks to raise error mid-stream
                     self._chunks.pop(0)
        except StopIteration:
            pass # End of stream
        except Exception as e:
             # Re-raise any explicitly configured error or other unexpected ones
             raise e


class Response:
    """Simplified Response class focusing on iter_content."""
    def __init__(self, raw_stream_object=None):
        self.raw = raw_stream_object if raw_stream_object else RawStream()
        self.reason = "OK"
        self.status_code = 200

    def iter_content(self, chunk_size=1, decode_unicode=False):
        """
        Iterates over the response data.

        This method simulates the core logic where exceptions during
        streaming need to be handled.
        """
        def generate():
            try:
                # In the base version, we only anticipate DecodeError
                # from the raw stream's handling (simplified).
                for chunk in self.raw.stream(chunk_size=chunk_size, decode_content=True):
                    yield chunk
            except DecodeError as e:
                 # Handle known decoding issues
                 raise ContentDecodingError(e)
            # Base version does NOT explicitly handle SocketError or ReadTimeoutError here

        return generate()

    def raise_for_status(self):
        """Raises an exception for bad status codes (simplified)."""
        if 400 <= self.status_code < 600:
            raise Exception(f"HTTP Error: {self.status_code} {self.reason}")

    @property
    def content(self):
        """Read the entire response content."""
        return b"".join(list(self.iter_content()))

# Example Usage (Optional - helps verify base code works)
if __name__ == '__main__':
    print("--- Base Code Execution ---")

    # Simulate a successful response
    print("Successful iteration:")
    response_ok = Response(RawStream(data_chunks=[b'Data', b' ', b'Part 1']))
    for chunk in response_ok.iter_content():
        print(f"  Received chunk: {chunk}")
    print(f"  Full content: {response_ok.content}")

    # Simulate a response where the raw stream raises DecodeError
    print("\nIteration with DecodeError:")
    response_decode_err = Response(RawStream(error_to_raise=DecodeError))
    try:
        list(response_decode_err.iter_content())
    except ContentDecodingError as e:
        print(f"  Caught expected error: {e}")

    # Simulate a response where the raw stream raises an unexpected SocketError
    # In the base code, this will NOT be caught by iter_content's specific handlers.
    print("\nIteration with unhandled SocketError:")
    response_socket_err = Response(RawStream(error_to_raise=SocketError))
    try:
        list(response_socket_err.iter_content())
    except SocketError as e:
        print(f"  Caught raw error (unhandled by iter_content): {e}")
    except Exception as e:
        print(f"  Caught unexpected error: {e}")