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

class StreamingError(CustomBaseException):
    """Simulates a generic streaming error (like chunked encoding issues)."""
    pass # Added for merged code

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
            count = 0
            total_chunks = len(self._chunks)
            while True:
                count += 1
                # Raise the error mid-stream (e.g., after the first chunk)
                # or immediately if only one chunk was configured.
                if self._error_to_raise and (count > 1 or total_chunks <= 1):
                    raise self._error_to_raise("Simulated stream error")
                yield next(self._iterator)

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

        MERGED IMPLEMENTATION: Includes exception handling from both Feature 1
        (SocketError) and Feature 2 (ReadTimeoutError, ProtocolError).
        """
        def generate():
            try:
                for chunk in self.raw.stream(chunk_size=chunk_size, decode_content=True):
                    yield chunk
            except DecodeError as e:
                 # Base handling
                 raise ContentDecodingError(e)
            except ProtocolError as e:
                 # Added by Feature 2 (non-conflicting part)
                 # Mapping to a generic StreamingError for this example
                 raise StreamingError(e)
            except ReadTimeoutError as e:
                 # Added by Feature 2 (conflicting part - preferred timeout)
                 raise ConnectionError(e)
            except SocketError as e:
                 # Added by Feature 1 (conflicting part - lower-level error)
                 # Kept for robustness, might catch errors missed by ReadTimeoutError
                 # depending on the exact (simulated) underlying behavior.
                 raise ConnectionError(e)

        return generate()

    def raise_for_status(self):
        """Raises an exception for bad status codes (simplified)."""
        if 400 <= self.status_code < 600:
            raise Exception(f"HTTP Error: {self.status_code} {self.reason}")

    @property
    def content(self):
        """Read the entire response content."""
        return b"".join(list(self.iter_content()))

# Example Usage (Optional - helps verify merged code works)
if __name__ == '__main__':
    print("--- Merged Code Execution ---")

    # Simulate a successful response
    print("Successful iteration:")
    response_ok = Response(RawStream(data_chunks=[b'Merged', b' ', b'Data']))
    for chunk in response_ok.iter_content():
        print(f"  Received chunk: {chunk}")
    print(f"  Full content: {response_ok.content}")

    # Simulate Feature 1 requirement: SocketError -> ConnectionError
    print("\nIteration with SocketError:")
    response_socket_err = Response(RawStream(data_chunks=[b'a'], error_to_raise=SocketError))
    try:
        list(response_socket_err.iter_content())
    except ConnectionError as e:
        print(f"  Caught expected ConnectionError (from SocketError): {e}")
    except Exception as e:
        print(f"  Caught unexpected error: {e}")

    # Simulate Feature 2 requirement: ReadTimeoutError -> ConnectionError
    print("\nIteration with ReadTimeoutError:")
    response_timeout_err = Response(RawStream(data_chunks=[b'b'], error_to_raise=ReadTimeoutError))
    try:
        list(response_timeout_err.iter_content())
    except ConnectionError as e:
        print(f"  Caught expected ConnectionError (from ReadTimeoutError): {e}")
    except Exception as e:
        print(f"  Caught unexpected error: {e}")

    # Simulate Feature 2 requirement: ProtocolError -> StreamingError
    print("\nIteration with ProtocolError:")
    response_protocol_err = Response(RawStream(data_chunks=[b'c'], error_to_raise=ProtocolError))
    try:
        list(response_protocol_err.iter_content())
    except StreamingError as e:
        print(f"  Caught expected StreamingError (from ProtocolError): {e}")
    except Exception as e:
        print(f"  Caught unexpected error: {e}")

    # Simulate Base requirement: DecodeError -> ContentDecodingError
    print("\nIteration with DecodeError:")
    response_decode_err = Response(RawStream(data_chunks=[b'd'], error_to_raise=DecodeError))
    try:
        list(response_decode_err.iter_content())
    except ContentDecodingError as e:
        print(f"  Caught expected ContentDecodingError (from DecodeError): {e}")
    except Exception as e:
        print(f"  Caught unexpected error: {e}")