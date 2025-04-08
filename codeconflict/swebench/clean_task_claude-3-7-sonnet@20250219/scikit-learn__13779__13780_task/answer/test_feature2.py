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


class NoSampleWeightClassifier:
    """Simple classifier that does not support sample weights"""
    def __init__(self, value=1):
        self.value = value
        
    def fit(self, X, y):
        # Does not accept sample_weight
        return self
        
    def predict(self, X):
        return np.ones(len(X)) * self.value


class TestFeature2(unittest.TestCase):
    """Tests for Feature 2: Support 'drop' as an alternative to None for disabling estimators"""
    
    def test_drop_equivalent_to_none_classifier(self):
        # Create simple dataset
        X = np.array([[1, 2], [3, 4], [5, 6]])
        y = np.array([0, 1, 0])
        
        # Create estimators
        clf1 = DummyClassifier(value=0)
        clf2 = DummyClassifier(value=1)
        clf3 = DummyClassifier(value=2)
        
        # Create and fit with None
        voter_none = VotingClassifier(
            estimators=[('clf1', clf1), ('clf2', clf2), ('clf3', clf3)]
        )
        voter_none.fit(X, y)
        voter_none.set_params(clf1=None)
        voter_none.fit(X, y)
        pred_none = voter_none.predict(X)
        
        # Create and fit with 'drop'
        voter_drop = VotingClassifier(
            estimators=[('clf1', clf1), ('clf2', clf2), ('clf3', clf3)]
        )
        voter_drop.fit(X, y)
        voter_drop.set_params(clf1='drop')
        voter_drop.fit(X, y)
        pred_drop = voter_drop.predict(X)
        
        # Check both approaches give same results
        np.testing.assert_array_equal(pred_none, pred_drop)
        
        # Check that weights handling is equivalent
        weights = [2, 1, 1]
        
        voter_none = VotingClassifier(
            estimators=[('clf1', clf1), ('clf2', clf2), ('clf3', clf3)],
            weights=weights
        )
        voter_none.fit(X, y)
        voter_none.set_params(clf1=None)
        voter_none.fit(X, y)
        weight_none = voter_none._weights_not_none()
        
        voter_drop = VotingClassifier(
            estimators=[('clf1', clf1), ('clf2', clf2), ('clf3', clf3)],
            weights=weights
        )
        voter_drop.fit(X, y)
        voter_drop.set_params(clf1='drop')
        voter_drop.fit(X, y)
        weight_drop = voter_drop._weights_not_none()
        
        self.assertEqual(weight_none, weight_drop)
    
    def test_drop_equivalent_to_none_regressor(self):
        # Create simple dataset
        X = np.array([[1, 2], [3, 4], [5, 6]])
        y = np.array([0.1, 0.2, 0.3])
        
        # Create estimators
        reg1 = DummyRegressor(value=0.1)
        reg2 = DummyRegressor(value=0.2)
        reg3 = DummyRegressor(value=0.3)
        
        # Create and fit with None
        voter_none = VotingRegressor(
            estimators=[('reg1', reg1), ('reg2', reg2), ('reg3', reg3)]
        )
        voter_none.fit(X, y)
        voter_none.set_params(reg1=None)
        voter_none.fit(X, y)
        pred_none = voter_none.predict(X)
        
        # Create and fit with 'drop'
        voter_drop = VotingRegressor(
            estimators=[('reg1', reg1), ('reg2', reg2), ('reg3', reg3)]
        )
        voter_drop.fit(X, y)
        voter_drop.set_params(reg1='drop')
        voter_drop.fit(X, y)
        pred_drop = voter_drop.predict(X)
        
        # Check both approaches give same results
        np.testing.assert_array_almost_equal(pred_none, pred_drop)
    
    def test_sample_weight_error_message(self):
        # Create simple dataset
        X = np.array([[1, 2], [3, 4], [5, 6]])
        y = np.array([0, 1, 0])
        sample_weight = np.array([1.0, 2.0, 1.0])
        
        # Create estimators, one without sample_weight support
        clf1 = DummyClassifier(value=0)
        clf2 = NoSampleWeightClassifier(value=1)
        
        # Create voting classifier
        voter = VotingClassifier(
            estimators=[('clf1', clf1), ('clf2', clf2)]
        )
        
        # Check that proper error message is raised
        with self.assertRaises(ValueError) as context:
            voter.fit(X, y, sample_weight=sample_weight)
        
        self.assertIn("does not support sample weights", str(context.exception))
        self.assertIn("NoSampleWeightClassifier", str(context.exception))
    
    def test_all_estimators_none_or_drop(self):
        # Create simple dataset
        X = np.array([[1, 2], [3, 4], [5, 6]])
        y = np.array([0, 1, 0])
        
        # Create estimators
        clf1 = DummyClassifier(value=0)
        clf2 = DummyClassifier(value=1)
        
        # Create voting classifier
        voter = VotingClassifier(
            estimators=[('clf1', clf1), ('clf2', clf2)]
        )
        
        # Set all estimators to None
        voter.set_params(clf1=None, clf2=None)
        with self.assertRaises(ValueError) as context:
            voter.fit(X, y)
        self.assertIn('All estimators are None or "drop"', str(context.exception))
        
        # Set all estimators to 'drop'
        voter.set_params(clf1='drop', clf2='drop')
        with self.assertRaises(ValueError) as context:
            voter.fit(X, y)
        self.assertIn('All estimators are None or "drop"', str(context.exception))
        
        # Mix None and 'drop'
        voter.set_params(clf1=None, clf2='drop')
        with self.assertRaises(ValueError) as context:
            voter.fit(X, y)
        self.assertIn('All estimators are None or "drop"', str(context.exception))


if __name__ == '__main__':
    unittest.main()