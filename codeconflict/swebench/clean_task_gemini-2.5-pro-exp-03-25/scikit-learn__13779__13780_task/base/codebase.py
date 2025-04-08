# base/codebase.py
import inspect
import copy

class BaseProcessor:
    """Base class for processors to allow easy type checking if needed."""
    pass

class DoublingProcessor(BaseProcessor):
    """A simple processor that doubles the sum of data."""
    def process(self, data):
        print(f"DoublingProcessor processing data: {data}")
        return sum(data) * 2

    def supports_modifier(self):
        # Explicitly state it doesn't support the modifier
        return False

class ModifyingProcessor(BaseProcessor):
    """A processor that applies a modifier."""
    def process(self, data, modifier=1):
        print(f"ModifyingProcessor processing data: {data} with modifier: {modifier}")
        return sum(data) * modifier

    def supports_modifier(self):
        # Explicitly state it supports the modifier
        return True

class ProcessorEnsemble:
    """
    Manages and applies a collection of processors to data.
    Initial version has a bug when handling None processors with modifiers.
    """
    def __init__(self, processors):
        """
        Initializes the ensemble.

        Args:
            processors (list): A list of tuples, where each tuple is
                               (processor_name: str, processor_instance: object/None).
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
        """Sets processor parameters. Allows setting processors to None."""
        valid_params = self.get_params()
        for key, value in params.items():
            if key in valid_params:
                self.named_processors[key] = value
            else:
                raise ValueError(f"Invalid parameter {key} for ProcessorEnsemble")
        # Update the list view
        self.processors = list(self.named_processors.items())
        return self

    def apply(self, data, modifier=None):
        """
        Applies the processors to the data.

        Args:
            data (list): The input data (e.g., a list of numbers).
            modifier (int, optional): An optional modifier to pass to processors
                                      that support it. Defaults to None.

        Returns:
            int: The aggregated result (sum of processor outputs).

        Raises:
            ValueError: If a modifier is provided but an active processor
                        doesn't support it.
            AttributeError: (BUG!) If a processor is None and modifier is not None,
                            this version crashes trying to check support.
            ValueError: If all processors are None.
        """
        results = []
        active_processors_list = [] # Track processors that actually run

        # --- Potential Conflict Area START ---

        # BUGGY PART FOR FEATURE 1:
        # This check runs *before* checking if 'proc' is None, causing an error.
        if modifier is not None:
            for name, proc in self.processors:
                # This line will raise AttributeError if proc is None!
                if not hasattr(proc, 'supports_modifier') or not proc.supports_modifier():
                    # To avoid crashing *after* the AttributeError, we add a check here,
                    # but the damage might already be done in the condition above.
                    if proc is not None:
                        raise ValueError(f"Processor '{name}' does not support modifier.")
                    # If proc was None, AttributeError was raised by hasattr/supports_modifier() call.

        # Iterate and process *active* processors
        # FEATURE 2 will change the condition `proc is not None`
        for name, proc in self.processors:
            if proc is not None: # Base version only processes non-None
                active_processors_list.append(proc)
                if modifier is not None:
                    # We assume the check above passed or wasn't needed for this processor
                    if hasattr(proc, 'supports_modifier') and proc.supports_modifier():
                        results.append(proc.process(data, modifier=modifier))
                    else:
                        # If modifier provided but not supported by this specific proc,
                        # run without it (or raise error - let's run without for simplicity here)
                        # Note: the check above should have caught unsupported ones if modifier != None
                         results.append(proc.process(data))

                else: # Modifier is None
                    results.append(proc.process(data))

        # --- Potential Conflict Area END ---

        if not active_processors_list:
             # FEATURE 2 will change this error message
            raise ValueError("All processors are None. At least one is required!")

        self.active_processors_ = [p for name, p in self.processors if p in active_processors_list]

        # Simple aggregation: sum
        print(f"Aggregated result: {sum(results)}")
        return sum(results)

# Example Usage (Optional - for direct execution testing)
if __name__ == '__main__':
    proc_list = [
        ('doubler', DoublingProcessor()),
        ('modifier', ModifyingProcessor())
    ]
    ensemble = ProcessorEnsemble(proc_list)
    data_input = [1, 2, 3] # sum is 6

    print("--- Test Case 1: Standard run ---")
    result1 = ensemble.apply(data_input)
    # Expected: Doubler(6*2=12) + Modifier(6*1=6) = 18
    print(f"Result 1: {result1}") # Should be 18

    print("\n--- Test Case 2: Run with modifier ---")
    result2 = ensemble.apply(data_input, modifier=5)
    # Expected: Doubler(6*2=12) + Modifier(6*5=30) = 42
    print(f"Result 2: {result2}") # Should be 42

    print("\n--- Test Case 3: Set one processor to None (no modifier) ---")
    ensemble.set_params(doubler=None)
    result3 = ensemble.apply(data_input)
    # Expected: Modifier(6*1=6) = 6
    print(f"Result 3: {result3}") # Should be 6

    print("\n--- Test Case 4: Set one processor to None (WITH modifier - BUGGY!) ---")
    # Reset
    ensemble = ProcessorEnsemble([
        ('doubler', DoublingProcessor()),
        ('modifier', ModifyingProcessor())
    ])
    ensemble.set_params(modifier=None) # Set the one *with* modifier support to None
    try:
        result4 = ensemble.apply(data_input, modifier=5)
        print(f"Result 4: {result4}")
    except Exception as e:
        print(f"Caught expected error: {type(e).__name__}: {e}") # Expect AttributeError

    print("\n--- Test Case 5: All processors None ---")
    ensemble.set_params(doubler=None, modifier=None)
    try:
        result5 = ensemble.apply(data_input)
        print(f"Result 5: {result5}")
    except Exception as e:
        print(f"Caught expected error: {type(e).__name__}: {e}") # Expect ValueError