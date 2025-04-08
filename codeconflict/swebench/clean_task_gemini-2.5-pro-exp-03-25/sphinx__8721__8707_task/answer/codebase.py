# answer/codebase.py
# Represents the merged code incorporating both features.

class OutputGenerator:
    """
    A simple class to simulate generating output based on a builder type.
    This version incorporates logic from both Feature 1 and Feature 2.
    """
    def __init__(self, builder_name, config=None):
        """
        Initializes the generator.

        Args:
            builder_name (str): The name of the builder (e.g., 'html', 'epub', 'singlehtml').
            config (dict, optional): Configuration options. Defaults to {}.
                                     Expected key: 'enable_epub' (bool).
        """
        self.builder_name = builder_name
        self.config = config if config is not None else {}
        # Set default for clarity, mirroring sphinx's viewcode_enable_epub
        if 'enable_epub' not in self.config:
            self.config['enable_epub'] = False

    def _is_supported_builder(self):
        """
        Checks if the current builder should generate output.
        This helper incorporates logic from both features, similar to
        the refactoring in the real Feature 2 patch.

        Returns:
            bool: True if output should be generated, False otherwise.
        """
        # Condition from Feature 2: Skip 'singlehtml'
        if self.builder_name == "singlehtml":
            # print(f"Debug: Skipping {self.builder_name} (Feature 2 rule)")
            return False

        # Condition from Feature 1: Skip 'epub' if 'enable_epub' is false
        if self.builder_name == "epub" and not self.config.get('enable_epub', False):
            # print(f"Debug: Skipping {self.builder_name} (Feature 1 rule - epub disabled)")
            return False

        # Assume 'html' is always supported if not explicitly skipped above
        if self.builder_name == "html":
            # print(f"Debug: Supporting {self.builder_name}")
            return True

        # Assume 'epub' is supported if we reached here (means enable_epub is True)
        if self.builder_name == "epub":
             # print(f"Debug: Supporting {self.builder_name} (Feature 1 rule - epub enabled)")
             return True

        # Default: Assume other unknown builders are not supported for this example
        # print(f"Debug: Skipping unknown builder {self.builder_name}")
        return False

    def generate(self):
        """
        Generates the output string only if the builder is supported.

        Returns:
            str: A message indicating whether output was generated or skipped.
        """
        if self._is_supported_builder():
            # print(f"Merged: Generating output for builder: {self.builder_name}")
            return f"Output generated for {self.builder_name}"
        else:
            # print(f"Merged: Skipping output generation for builder: {self.builder_name}")
            return f"Output skipped for {self.builder_name}"