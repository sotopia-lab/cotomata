# Feature 1: Handle Socket Errors in Response Streaming

Catch and wrap socket.error exceptions in the Response.iter_content method to ensure they are properly converted to a ConnectionError exception, providing consistent error handling behavior for all connection-related issues.