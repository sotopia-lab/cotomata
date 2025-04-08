import unittest
import numpy as np
from codebase import VotingClassifier, VotingRegressor


class DummyClassifier:
    """Simple classifier that supports sample weights"""
    def __init__(self, value=1):
        self.value = value
        self.sample_weight_used = None
        
    def fit(self, X, y, sample_weight=None):
        self.sample_weight_used = sample_weight
        return self
        
    def predict(self, X):
        return np.ones(len(X)) * self.value


class DummyRegressor:
    """Simple regressor that supports sample weights"""
    def __init__(self, value=1.0):
        self.value = value
        self.sample_weight_used = None
        
    def fit(self, X, y, sample_weight=None):
        self.sample_weight_used = sample_weight
        return self
        
    def predict(self, X):
        return np.ones(len(X)) * self.value


class TestFeature1(unittest.TestCase):
    """Tests for Feature 1: Allow fitting with sample weights when an estimator is None"""
    
    def test_voting_classifier_with_none_estimator_and_weights(self):
        # Create simple dataset
        X = np.array([[1, 2], [3, 4], [5, 6]])
        y = np.array([0, 1, 0])
        sample_weight = np.array([1.0, 2.0, 1.0])
        
        # Create estimators
        clf1 = DummyClassifier(value=0)
        clf2 = DummyClassifier(value=1)
        
        # Create and fit voting classifier with all estimators
        voter = VotingClassifier(
            estimators=[('clf1', clf1), ('clf2', clf2)]
        )
        voter.fit(X, y, sample_weight=sample_weight)
        
        # Check that sample weights were passed to each estimator
        self.assertIsNotNone(voter.named_estimators_['clf1'].sample_weight_used)
        self.assertIsNotNone(voter.named_estimators_['clf2'].sample_weight_used)
        
        # Set one estimator to None and fit again
        voter.set_params(clf1=None)
        voter.fit(X, y, sample_weight=sample_weight)
        
        # Check prediction works
        y_pred = voter.predict(X)
        self.assertEqual(len(y_pred), len(y))
        
        # Check that the named_estimators_ only contains clf2
        self.assertIn('clf2', voter.named_estimators_)
        self.assertNotIn('clf1', voter.named_estimators_)
    
    def test_voting_regressor_with_none_estimator_and_weights(self):
        # Create simple dataset
        X = np.array([[1, 2], [3, 4], [5, 6]])
        y = np.array([0.1, 0.2, 0.3])
        sample_weight = np.array([1.0, 2.0, 1.0])
        
        # Create estimators
        reg1 = DummyRegressor(value=0.1)
        reg2 = DummyRegressor(value=0.2)
        
        # Create and fit voting regressor with all estimators
        voter = VotingRegressor(
            estimators=[('reg1', reg1), ('reg2', reg2)]
        )
        voter.fit(X, y, sample_weight=sample_weight)
        
        # Check that sample weights were passed to each estimator
        self.assertIsNotNone(voter.named_estimators_['reg1'].sample_weight_used)
        self.assertIsNotNone(voter.named_estimators_['reg2'].sample_weight_used)
        
        # Set one estimator to None and fit again
        voter.set_params(reg1=None)
        voter.fit(X, y, sample_weight=sample_weight)
        
        # Check prediction works
        y_pred = voter.predict(X)
        self.assertEqual(len(y_pred), len(y))
        
        # Check that only reg2 is in named_estimators_
        self.assertIn('reg2', voter.named_estimators_)
        self.assertNotIn('reg1', voter.named_estimators_)


if __name__ == '__main__':
    unittest.main()