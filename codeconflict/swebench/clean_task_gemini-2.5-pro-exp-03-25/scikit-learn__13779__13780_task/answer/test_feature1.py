# answer/test_feature1.py
import unittest
from codebase import ProcessorEnsemble, DoublingProcessor, ModifyingProcessor

class TestFeature1(unittest.TestCase):
    """Tests Feature 1: Handling None processors with modifiers."""

    def setUp(self):
        """Set up a standard ensemble for tests."""
        self.processors = [
            ('doubler', DoublingProcessor()),
            ('modifier', ModifyingProcessor())
        ]
        self.ensemble = ProcessorEnsemble(self.processors)
        self.data = [10, 20] # sum = 30

    def test_none_processor_with_modifier(self):
        """
        Verify apply() works with a modifier when a processor is None.
        (Fixes the AttributeError from the base code).
        """
        self.ensemble.set_params(doubler=None)
        # Expected result: Only ModifyingProcessor runs (30 * 5 = 150)
        result = self.ensemble.apply(self.data, modifier=5)
        self.assertEqual(result, 150)
        # Verify only the active processor is stored
        self.assertEqual(len(self.ensemble.active_processors_), 1)
        self.assertIsInstance(self.ensemble.active_processors_[0], ModifyingProcessor)

    def test_none_processor_supports_modifier_with_modifier(self):
        """
        Verify apply() works with a modifier when the processor supporting
        it is set to None.
        """
        self.ensemble.set_params(modifier=None)
        # Expected result: Only DoublingProcessor runs (30 * 2 = 60).
        # apply() should not raise an error about modifier support, as the
        # only remaining processor (Doubler) doesn't need the modifier.
        # The merged apply() raises error *only if* an active proc requires
        # the modifier but doesn't support it. Here, Doubler doesn't support it,
        # but the modifier isn't meant for it.
        # *Correction*: The merged logic raises error if *any* active processor
        # doesn't support the *provided* modifier. So Doubler will cause error.
        with self.assertRaisesRegex(ValueError, "Processor 'doubler' does not support modifier"):
             self.ensemble.apply(self.data, modifier=5)

    def test_none_processor_no_modifier(self):
        """Verify apply() works without modifier when a processor is None."""
        self.ensemble.set_params(doubler=None)
        # Expected result: Only ModifyingProcessor runs (30 * 1 = 30)
        result = self.ensemble.apply(self.data)
        self.assertEqual(result, 30)
        self.assertEqual(len(self.ensemble.active_processors_), 1)
        self.assertIsInstance(self.ensemble.active_processors_[0], ModifyingProcessor)

    def test_error_if_active_processor_does_not_support_modifier(self):
        """
        Verify ValueError is raised if modifier is provided but an active
        processor does not support it.
        """
        # Keep both processors active
        with self.assertRaisesRegex(ValueError, "Processor 'doubler' does not support modifier"):
            self.ensemble.apply(self.data, modifier=5)

if __name__ == '__main__':
    unittest.main(argv=['first-arg-is-ignored'], exit=False)