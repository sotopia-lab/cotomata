# base/codebase.py
# Represents the original state before feature implementations.

class OutputGenerator:
    """
    A simple class to simulate generating output based on a builder type.
    In the base version, it always attempts to generate output.
    """
    def __init__(self, builder_name, config=None):
        """
        Initializes the generator.

        Args:
            builder_name (str): The name of the builder (e.g., 'html', 'epub').
            config (dict, optional): Configuration options. Defaults to {}.
                                     Expected key: 'enable_epub' (bool).
        """
        self.builder_name = builder_name
        self.config = config if config is not None else {}
        # Set default for clarity, mirroring sphinx's viewcode_enable_epub
        if 'enable_epub' not in self.config:
            self.config['enable_epub'] = False

    def generate(self):
        """
        Generates the output string. In this base version, it always generates.
        Features will add conditions to skip generation.

        Returns:
            str: A message indicating whether output was generated.
        """
        # Base logic: Always generate regardless of builder type or config
        print(f"Base: Generating output for builder: {self.builder_name}")
        return f"Output generated for {self.builder_name}"