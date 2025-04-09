import unittest
import numpy as np
from codebase import VotingEstimator

class SimpleEstimator:
    """A simple estimator that supports sample weights."""
    def __init__(self, value=1.0):
        self.value = value
        self.is_fitted = False
        
    def fit(self, X, y, sample_weight=None):
        self.is_fitted = True
        self.sample_weight_used = sample_weight is not None
        return self
        
    def predict(self, X):
        return np.ones(len(X)) * self.value

class EstimatorWithoutWeights:
    """A simple estimator that doesn't support sample weights."""
    def __init__(self, value=1.0):
        self.value = value
        self.is_fitted = False
        
    def fit(self, X, y):
        self.is_fitted = True
        return self
        
    def predict(self, X):
        return np.ones(len(X)) * self.value

class TestFeature1(unittest.TestCase):
    def setUp(self):
        # Create sample data
        self.X = np.array([[1, 2], [3, 4], [5, 6]])
        self.y = np.array([1, 2, 3])
        self.sample_weight = np.ones(3)
        
    def test_fit_with_none_estimator_and_sample_weight(self):
        """Test that VotingEstimator can fit with None estimator and sample weights."""
        # Create estimators
        est1 = SimpleEstimator(1.0)
        est2 = SimpleEstimator(2.0)
        
        # Create and fit VotingEstimator
        voting = VotingEstimator(estimators=[('est1', est1), ('est2', est2)])
        voting.fit(self.X, self.y, sample_weight=self.sample_weight)
        
        # Set one estimator to None and verify it still fits with sample weights
        voting.estimators = [('est1', None), ('est2', est2)]
        voting.fit(self.X, self.y, sample_weight=self.sample_weight)
        
        # Verify the predictions still work
        predictions = voting.predict(self.X)
        self.assertEqual(predictions.shape, self.y.shape)
        self.assertTrue(np.allclose(predictions, 2.0))  # Only est2 is used
        
    def test_handles_multiple_none_estimators(self):
        """Test that VotingEstimator handles multiple None estimators."""
        # Create estimators
        est1 = SimpleEstimator(1.0)
        est2 = SimpleEstimator(2.0)
        est3 = SimpleEstimator(3.0)
        
        # Create VotingEstimator
        voting = VotingEstimator(estimators=[
            ('est1', est1), ('est2', est2), ('est3', est3)
        ])
        
        # Fit with all estimators
        voting.fit(self.X, self.y, sample_weight=self.sample_weight)
        
        # Set multiple estimators to None and verify it still fits
        voting.estimators = [('est1', None), ('est2', None), ('est3', est3)]
        voting.fit(self.X, self.y, sample_weight=self.sample_weight)
        
        # Verify predictions still work
        predictions = voting.predict(self.X)
        self.assertEqual(predictions.shape, self.y.shape)
        self.assertTrue(np.allclose(predictions, 3.0))  # Only est3 is used
        
    def test_error_when_all_estimators_none(self):
        """Test that VotingEstimator raises error when all estimators are None."""
        # Create estimators
        est1 = SimpleEstimator(1.0)
        est2 = SimpleEstimator(2.0)
        
        # Create VotingEstimator with all None estimators
        voting = VotingEstimator(estimators=[('est1', None), ('est2', None)])
        
        # Verify it raises an error
        with self.assertRaises(ValueError) as context:
            voting.fit(self.X, self.y, sample_weight=self.sample_weight)
        
        self.assertIn('All estimators are None or "drop"', str(context.exception))
        
    def test_error_when_estimator_doesnt_support_weights(self):
        """Test error when an estimator doesn't support sample weights."""
        # Create estimators
        est1 = SimpleEstimator(1.0)
        est2 = EstimatorWithoutWeights(2.0)
        
        # Create VotingEstimator
        voting = VotingEstimator(estimators=[('est1', est1), ('est2', est2)])
        
        # Verify it raises an error about sample weights
        with self.assertRaises(ValueError) as context:
            voting.fit(self.X, self.y, sample_weight=self.sample_weight)
        
        self.assertIn("does not support sample weights", str(context.exception))
        
        # Set the unsupported estimator to None and verify it works
        voting.estimators = [('est1', est1), ('est2', None)]
        voting.fit(self.X, self.y, sample_weight=self.sample_weight)
        
        # Verify predictions work
        predictions = voting.predict(self.X)
        self.assertEqual(predictions.shape, self.y.shape)

if __name__ == '__main__':
    unittest.main()