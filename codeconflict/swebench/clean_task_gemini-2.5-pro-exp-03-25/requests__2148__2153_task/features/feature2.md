markdown
Handle `ReadTimeoutError` and `ProtocolError` from the underlying stream during content iteration, wrapping timeout errors as `ConnectionError`.