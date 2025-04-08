# Feature 1: Catch and Wrap socket.error in a ConnectionError

Handle socket.error exceptions by catching them in the iter_content method and rewrapping them as ConnectionError exceptions, ensuring consistent error handling throughout the library.