class VotingEstimator:
    """
    A voting estimator that combines multiple machine learning models.
    
    Parameters
    ----------
    estimators : list of (string, estimator) tuples
        List of (name, estimator) tuples to be used in the ensemble.
        An estimator can be set to None using set_params.
    
    weights : list, optional (default=None)
        Sequence of weights for each estimator. If None, all estimators have equal weight.
    """
    
    def __init__(self, estimators, weights=None):
        self.estimators = estimators
        self.weights = weights
        self.estimators_ = None
        
    def fit(self, X, y, sample_weight=None):
        """
        Fit the voting estimator.
        
        Parameters
        ----------
        X : array-like, shape (n_samples, n_features)
            Training vectors.
        y : array-like, shape (n_samples,)
            Target values.
        sample_weight : array-like, shape (n_samples,), optional
            Sample weights for training.
            
        Returns
        -------
        self : object
        """
        if self.weights is not None and len(self.weights) != len(self.estimators):
            raise ValueError('Number of weights must match number of estimators;'
                            f' got {len(self.weights)} weights, {len(self.estimators)} estimators')
        
        # Validate that we have at least one estimator that is not None
        if all(estimator is None for _, estimator in self.estimators):
            raise ValueError('All estimators are None. At least one is required!')
        
        # Check if sample_weight can be used with all estimators
        if sample_weight is not None:
            for name, estimator in self.estimators:
                if estimator is None:
                    continue
                if not hasattr(estimator, 'fit') or not self._accepts_sample_weight(estimator):
                    raise ValueError(f"Underlying estimator '{name}' does not support sample weights.")
        
        # Fit each estimator
        self.estimators_ = []
        for name, estimator in self.estimators:
            if estimator is not None:
                # Clone the estimator to avoid modifying the original
                est_copy = self._clone(estimator)
                # Fit with sample_weight if provided
                if sample_weight is not None:
                    est_copy.fit(X, y, sample_weight=sample_weight)
                else:
                    est_copy.fit(X, y)
                self.estimators_.append((name, est_copy))
        
        return self
    
    def predict(self, X):
        """
        Predict class labels for X.
        
        Parameters
        ----------
        X : array-like, shape (n_samples, n_features)
            The input samples.
            
        Returns
        -------
        y_pred : array-like, shape (n_samples,)
            The predicted classes.
        """
        if self.estimators_ is None:
            raise ValueError("Estimator not fitted, call 'fit' before making predictions!")
        
        # Simple implementation: average predictions from all estimators
        predictions = []
        weights = self._get_weights()
        
        for idx, (name, estimator) in enumerate(self.estimators_):
            pred = estimator.predict(X)
            weight = 1.0 if weights is None else weights[idx]
            predictions.append((pred, weight))
        
        # Combine predictions (simple average for this example)
        final_pred = sum(pred * weight for pred, weight in predictions) / sum(
            weight for _, weight in predictions)
        
        return final_pred
    
    def _get_weights(self):
        """Get weights for the active estimators."""
        if self.weights is None:
            return None
        
        # Filter weights for only the active estimators (not None)
        active_weights = []
        active_idx = 0
        
        for idx, (_, estimator) in enumerate(self.estimators):
            if estimator is not None:
                active_weights.append(self.weights[idx])
                active_idx += 1
                
        return active_weights
    
    def _accepts_sample_weight(self, estimator):
        """Check if estimator's fit method accepts sample_weight parameter."""
        return 'sample_weight' in estimator.fit.__code__.co_varnames
    
    def _clone(self, estimator):
        """Create a copy of the estimator."""
        # In a real implementation, this would create a deep copy
        # For simplicity, we'll assume estimators are already properly cloned
        return estimator