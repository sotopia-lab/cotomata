# answer/codebase.py
import inspect
import copy

class BaseProcessor:
    """Base class for processors to allow easy type checking if needed."""
    pass

class DoublingProcessor(BaseProcessor):
    """A simple processor that doubles the sum of data."""
    def process(self, data):
        # print(f"DoublingProcessor processing data: {data}")
        return sum(data) * 2

    def supports_modifier(self):
        # Explicitly state it doesn't support the modifier
        return False

class ModifyingProcessor(BaseProcessor):
    """A processor that applies a modifier."""
    def process(self, data, modifier=1):
        # print(f"ModifyingProcessor processing data: {data} with modifier: {modifier}")
        return sum(data) * modifier

    def supports_modifier(self):
        # Explicitly state it supports the modifier
        return True

class ProcessorEnsemble:
    """
    Manages and applies a collection of processors to data.
    Merged version handles None/'drop' processors correctly and modifiers safely.
    """
    # Define constants for disabling processors
    _DROP_ESTIMATOR = "drop"

    def __init__(self, processors):
        """
        Initializes the ensemble.

        Args:
            processors (list): A list of tuples, where each tuple is
                               (processor_name: str, processor_instance: object/None/'drop').
                               processor_instance should have a 'process' method.
        """
        if not all(isinstance(name, str) for name, _ in processors):
             raise ValueError("Processor names must be strings.")
        self.processors = processors
        self.named_processors = dict(processors)
        self._validate_names()
        self.active_processors_ = [] # To store fitted/active processors

    def _validate_names(self):
        names = [name for name, _ in self.processors]
        if len(set(names)) != len(names):
            raise ValueError("Processor names must be unique.")

    def get_params(self):
        """Gets processor parameters."""
        return copy.deepcopy(dict(self.processors))

    def set_params(self, **params):
        """Sets processor parameters. Allows setting processors to None or 'drop'."""
        valid_params = self.get_params()
        for key, value in params.items():
            if key in valid_params:
                 # Allow setting to None or 'drop'
                if value is None or value == self._DROP_ESTIMATOR or isinstance(value, BaseProcessor):
                    self.named_processors[key] = value
                else:
                    raise TypeError(f"Processor value for '{key}' must be a Processor instance, None, or 'drop'")
            else:
                raise ValueError(f"Invalid parameter {key} for ProcessorEnsemble")
        # Update the list view
        self.processors = list(self.named_processors.items())
        return self

    def apply(self, data, modifier=None):
        """
        Applies the processors to the data. Handles None and 'drop' processors.

        Args:
            data (list): The input data (e.g., a list of numbers).
            modifier (int, optional): An optional modifier to pass to processors
                                      that support it. Defaults to None.

        Returns:
            int: The aggregated result (sum of processor outputs).

        Raises:
            ValueError: If a modifier is provided but an active processor
                        doesn't support it.
            ValueError: If all processors are None or 'drop'.
        """
        results = []
        processed_processor_names = [] # Keep track of names of processors that ran

        # Merged Logic: Iterate and check status *before* any operation
        for name, proc in self.processors:
            # Feature 2 check: Skip if None or 'drop'
            if proc not in (None, self._DROP_ESTIMATOR):
                # Feature 1 fix incorporated: Only check support for non-disabled processors
                if modifier is not None:
                    if not hasattr(proc, 'supports_modifier') or not proc.supports_modifier():
                        raise ValueError(f"Processor '{name}' does not support modifier.")

                # Process the active processor
                if modifier is not None and hasattr(proc, 'supports_modifier') and proc.supports_modifier():
                     results.append(proc.process(data, modifier=modifier))
                     processed_processor_names.append(name)
                elif modifier is None: # Process without modifier if modifier not provided
                     results.append(proc.process(data))
                     processed_processor_names.append(name)
                # Note: If modifier is provided but not supported, the check above raised ValueError

        # Check if any processors actually ran
        if not processed_processor_names:
             # Feature 2 updated error message
            raise ValueError("All processors are None or 'drop'. At least one is required!")

        # Store the active processors based on who ran
        self.active_processors_ = [p for name, p in self.processors if name in processed_processor_names]

        # Simple aggregation: sum
        # print(f"Aggregated result: {sum(results)}")
        return sum(results)

# Example Usage (Optional - for direct execution testing)
if __name__ == '__main__':
    proc_list = [
        ('doubler', DoublingProcessor()),
        ('modifier', ModifyingProcessor())
    ]
    ensemble = ProcessorEnsemble(proc_list)
    data_input = [1, 2, 3] # sum is 6

    print("--- Merged Test Case 1: Standard run ---")
    result1 = ensemble.apply(data_input)
    print(f"Result 1: {result1}") # Expected: 18

    print("\n--- Merged Test Case 2: Run with modifier ---")
    result2 = ensemble.apply(data_input, modifier=5)
    print(f"Result 2: {result2}") # Expected: 42

    print("\n--- Merged Test Case 3a: Set one processor to None (WITH modifier - FIXED!) ---")
    ensemble.set_params(doubler=None)
    result3a = ensemble.apply(data_input, modifier=5)
    print(f"Result 3a: {result3a}") # Expected: Modifier(6*5=30) = 30

    print("\n--- Merged Test Case 3b: Set one processor to 'drop' (WITH modifier) ---")
    # Reset
    ensemble = ProcessorEnsemble([
        ('doubler', DoublingProcessor()),
        ('modifier', ModifyingProcessor())
    ])
    ensemble.set_params(modifier='drop') # Use 'drop'
    result3b = ensemble.apply(data_input, modifier=5)
    # Expected: Doubler(6*2=12) = 12 (modifier not applicable)
    print(f"Result 3b: {result3b}") # Expected: 12 (Doubler ran, Modifier dropped)


    print("\n--- Merged Test Case 4: Check unsupported modifier error ---")
    # Reset
    ensemble = ProcessorEnsemble([
        ('doubler', DoublingProcessor()),
        ('modifier', ModifyingProcessor())
    ])
    ensemble.set_params(modifier=None) # Keep doubler, drop modifier
    try:
        # Doubler doesn't support modifier, should raise error
        result4 = ensemble.apply(data_input, modifier=5)
        print(f"Result 4: {result4}")
    except Exception as e:
        print(f"Caught expected error: {type(e).__name__}: {e}") # Expect ValueError

    print("\n--- Merged Test Case 5: All processors None/drop ---")
    ensemble.set_params(doubler=None, modifier='drop')
    try:
        result5 = ensemble.apply(data_input)
        print(f"Result 5: {result5}")
    except Exception as e:
        print(f"Caught expected error: {type(e).__name__}: {e}") # Expect ValueError (new message)