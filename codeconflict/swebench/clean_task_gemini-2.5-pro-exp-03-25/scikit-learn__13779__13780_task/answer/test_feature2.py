# answer/test_feature2.py
import unittest
from codebase import ProcessorEnsemble, DoublingProcessor, ModifyingProcessor

class TestFeature2(unittest.TestCase):
    """Tests Feature 2: Allowing 'drop' to disable processors."""

    def setUp(self):
        """Set up a standard ensemble for tests."""
        self.processors = [
            ('doubler', DoublingProcessor()),
            ('modifier', ModifyingProcessor())
        ]
        self.ensemble = ProcessorEnsemble(self.processors)
        self.data = [10, 20] # sum = 30

    def test_drop_processor_no_modifier(self):
        """Verify 'drop' disables a processor when no modifier is used."""
        self.ensemble.set_params(doubler='drop')
        # Expected result: Only ModifyingProcessor runs (30 * 1 = 30)
        result = self.ensemble.apply(self.data)
        self.assertEqual(result, 30)
        self.assertEqual(len(self.ensemble.active_processors_), 1)
        self.assertIsInstance(self.ensemble.active_processors_[0], ModifyingProcessor)

    def test_drop_processor_with_modifier(self):
        """Verify 'drop' disables a processor when a modifier is used."""
        self.ensemble.set_params(doubler='drop')
        # Expected result: Only ModifyingProcessor runs (30 * 5 = 150)
        result = self.ensemble.apply(self.data, modifier=5)
        self.assertEqual(result, 150)
        self.assertEqual(len(self.ensemble.active_processors_), 1)
        self.assertIsInstance(self.ensemble.active_processors_[0], ModifyingProcessor)

    def test_drop_processor_that_supports_modifier(self):
        """Verify 'drop' works when disabling the modifier-supporting processor."""
        self.ensemble.set_params(modifier='drop')
         # Expected result: Only DoublingProcessor runs (30 * 2 = 60)
         # Modifier = 5 is passed, but the only active proc (Doubler) doesn't support it.
         # This should raise the ValueError.
        with self.assertRaisesRegex(ValueError, "Processor 'doubler' does not support modifier"):
             self.ensemble.apply(self.data, modifier=5)

        # Test without modifier
        result_no_mod = self.ensemble.apply(self.data)
        self.assertEqual(result_no_mod, 60) # 30 * 2 = 60
        self.assertEqual(len(self.ensemble.active_processors_), 1)
        self.assertIsInstance(self.ensemble.active_processors_[0], DoublingProcessor)


    def test_all_processors_none(self):
        """Verify error when all processors are None."""
        self.ensemble.set_params(doubler=None, modifier=None)
        with self.assertRaisesRegex(ValueError, "All processors are None or 'drop'"):
            self.ensemble.apply(self.data)

    def test_all_processors_dropped(self):
        """Verify error when all processors are 'drop'."""
        self.ensemble.set_params(doubler='drop', modifier='drop')
        with self.assertRaisesRegex(ValueError, "All processors are None or 'drop'"):
            self.ensemble.apply(self.data)

    def test_mixed_none_and_drop(self):
        """Verify error when all processors are disabled using mix of None and 'drop'."""
        self.ensemble.set_params(doubler=None, modifier='drop')
        with self.assertRaisesRegex(ValueError, "All processors are None or 'drop'"):
            self.ensemble.apply(self.data)

    def test_set_params_rejects_invalid_value(self):
        """Verify set_params only accepts processors, None, or 'drop'."""
        with self.assertRaises(TypeError):
             self.ensemble.set_params(doubler=123) # Invalid type
        with self.assertRaises(TypeError):
             self.ensemble.set_params(modifier="keep") # Invalid string


if __name__ == '__main__':
    unittest.main(argv=['first-arg-is-ignored'], exit=False)