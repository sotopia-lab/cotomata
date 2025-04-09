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

class TestFeature2(unittest.TestCase):
    def setUp(self):
        # Create sample data
        self.X = np.array([[1, 2], [3, 4], [5, 6]])
        self.y = np.array([1, 2, 3])
        self.sample_weight = np.ones(3)
        
    def test_drop_works_same_as_none(self):
        """Test that 'drop' works the same as None for removing estimators."""
        # Create estimators
        est1 = SimpleEstimator(1.0)
        est2 = SimpleEstimator(2.0)
        
        # Create VotingEstimator with None for est1
        voting_none = VotingEstimator(estimators=[('est1', None), ('est2', est2)])
        voting_none.fit(self.X, self.y)
        pred_none = voting_none.predict(self.X)
        
        # Create VotingEstimator with 'drop' for est1
        voting_drop = VotingEstimator(estimators=[('est1', 'drop'), ('est2', est2)])
        voting_drop.fit(self.X, self.y)
        pred_drop = voting_drop.predict(self.X)
        
        # Verify predictions are the same
        np.testing.assert_array_equal(pred_none, pred_drop)
        
    def test_drop_with_sample_weights(self):
        """Test using 'drop' with sample weights."""
        # Create estimators
        est1 = SimpleEstimator(1.0)
        est2 = SimpleEstimator(2.0)
        
        # Create and fit VotingEstimator
        voting = VotingEstimator(estimators=[('est1', est1), ('est2', est2)])
        voting.fit(self.X, self.y, sample_weight=self.sample_weight)
        
        # Set one estimator to 'drop' and verify it still fits with sample weights
        voting.estimators = [('est1', 'drop'), ('est2', est2)]
        voting.fit(self.X, self.y, sample_weight=self.sample_weight)
        
        # Verify the predictions still work
        predictions = voting.predict(self.X)
        self.assertEqual(predictions.shape, self.y.shape)
        self.assertTrue(np.allclose(predictions, 2.0))  # Only est2 is used
        
    def test_weights_with_drop_estimators(self):
        """Test that weights are correctly assigned when using 'drop'."""
        # Create estimators
        est1 = SimpleEstimator(1.0)
        est2 = SimpleEstimator(2.0)
        est3 = SimpleEstimator(3.0)
        
        # Create VotingEstimator with weights
        weights = [1.0, 2.0, 3.0]
        voting = VotingEstimator(
            estimators=[('est1', est1), ('est2', est2), ('est3', est3)],
            weights=weights
        )
        
        # Fit with all estimators
        voting.fit(self.X, self.y)
        all_est_pred = voting.predict(self.X)
        
        # Expected prediction: (1*1 + 2*2 + 3*3) / (1 + 2 + 3) = 14/6 = 2.33
        expected_all = (1*1.0 + 2*2.0 + 3*3.0) / (1 + 2 + 3)
        self.assertTrue(np.allclose(all_est_pred, expected_all))
        
        # Set est2 to 'drop' and verify weights are adjusted correctly
        voting.estimators = [('est1', est1), ('est2', 'drop'), ('est3', est3)]
        voting.fit(self.X, self.y)
        drop_est_pred = voting.predict(self.X)
        
        # Expected prediction: (1*1 + 3*3) / (1 + 3) = 10/4 = 2.5
        expected_drop = (1*1.0 + 3*3.0) / (1 + 3)
        self.assertTrue(np.allclose(drop_est_pred, expected_drop))
        
    def test_error_when_all_estimators_drop(self):
        """Test that VotingEstimator raises error when all estimators are 'drop'."""
        # Create estimators
        est1 = SimpleEstimator(1.0)
        est2 = SimpleEstimator(2.0)
        
        # Create VotingEstimator with all 'drop' estimators
        voting = VotingEstimator(estimators=[('est1', 'drop'), ('est2', 'drop')])
        
        # Verify it raises an error
        with self.assertRaises(ValueError) as context:
            voting.fit(self.X, self.y)
        
        self.assertIn('All estimators are None or "drop"', str(context.exception))
        
    def test_mixed_none_and_drop(self):
        """Test that using a mix of None and 'drop' works correctly."""
        # Create estimators
        est1 = SimpleEstimator(1.0)
        est2 = SimpleEstimator(2.0)
        est3 = SimpleEstimator(3.0)
        
        # Create VotingEstimator with mixed None and 'drop'
        voting = VotingEstimator(estimators=[
            ('est1', None), ('est2', 'drop'), ('est3', est3)
        ])
        
        # Fit and verify it works
        voting.fit(self.X, self.y)
        predictions = voting.predict(self.X)
        
        # Only est3 should be used
        self.assertTrue(np.allclose(predictions, 3.0))

if __name__ == '__main__':
    unittest.main()