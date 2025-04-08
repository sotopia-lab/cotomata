import numpy as np
from joblib import Parallel, delayed


def clone(estimator):
    """Simple clone function for the example"""
    return estimator


class Bunch(dict):
    """Container object exposing keys as attributes"""
    def __init__(self, **kwargs):
        super().__init__(kwargs)
        self.__dict__ = self


class _BaseVoting:
    """Base class for Voting estimators"""
    
    def __init__(self, estimators, weights=None, n_jobs=None):
        self.estimators = estimators
        self.weights = weights
        self.n_jobs = n_jobs
    
    def _validate_estimators(self):
        if not self.estimators:
            raise ValueError("Invalid 'estimators' attribute, 'estimators' "
                             "should be a list of (string, estimator) tuples.")
        
        names, estimators = zip(*self.estimators)
        # validate names
        self._validate_names(names)
        
        # validate estimators
        for est in estimators:
            if est is not None and not hasattr(est, 'fit'):
                raise ValueError("All estimators should implement fit method, "
                                "or be None")
    
    def _validate_names(self, names):
        if len(set(names)) != len(names):
            raise ValueError("Names provided are not unique: {}".format(names))
        
    def fit(self, X, y, sample_weight=None):
        """Fit the estimators.
        
        Parameters
        ----------
        X : {array-like, sparse matrix}, shape (n_samples, n_features)
            Training vectors.
        y : array-like, shape (n_samples,)
            Target values.
        sample_weight : array-like, shape (n_samples,) or None
            Sample weights. If None, then samples are equally weighted.
            
        Returns
        -------
        self : object
        """
        self._validate_estimators()
        
        if self.weights is not None and len(self.weights) != len(self.estimators):
            raise ValueError('Number of weights must match number of'
                             ' estimators; got %d weights, %d estimators'
                             % (len(self.weights), len(self.estimators)))
        
        names, clfs = zip(*self.estimators)
        
        n_isnone = sum([clf is None for clf in clfs])
        if n_isnone == len(self.estimators):
            raise ValueError('All estimators are None. At least one is required!')
        
        # Fit estimators
        self.estimators_ = Parallel(n_jobs=self.n_jobs)(
            delayed(_parallel_fit_estimator)(clone(clf), X, y, sample_weight=sample_weight)
            for clf in clfs if clf is not None)
        
        # Create a dict mapping from label to estimator
        self.named_estimators_ = Bunch()
        for k, e in zip(self.estimators, self.estimators_):
            self.named_estimators_[k[0]] = e
        
        return self
    
    def _weights_not_none(self):
        """Get the weights of not `None` estimators"""
        if self.weights is None:
            return None
        return [w for est, w in zip(self.estimators, self.weights) 
                if est[1] is not None]
    
    def _predict(self, X):
        """Collect results from estimators' predict calls"""
        return [est.predict(X) for est in self.estimators_]


def _parallel_fit_estimator(estimator, X, y, sample_weight=None):
    """Private function used to fit an estimator within a job."""
    if sample_weight is not None:
        estimator.fit(X, y, sample_weight=sample_weight)
    else:
        estimator.fit(X, y)
    return estimator


class VotingClassifier(_BaseVoting):
    """Soft Voting/Majority Rule classifier.
    
    A voting classifier is an ensemble meta-classifier that fits base classifiers 
    each on the whole dataset and then uses average predicted probabilities 
    (soft voting) or class labels (hard voting) for prediction.
    
    Parameters
    ----------
    estimators : list of (string, estimator) tuples
        Invoking the ``fit`` method on the ``VotingClassifier`` will fit clones
        of those original estimators that will be stored in the class attribute
        ``self.estimators_``. An estimator can be set to `None` using
        ``set_params``.
    weights : array-like, shape (n_classifiers,), optional (default=None)
        If specified, the predicted class probabilities for each classifier are
        multiplied by the classifier weight. Uses uniform weights if None.
    n_jobs : int or None, optional (default=None)
        The number of jobs to run in parallel for ``fit``. None means 1.
    """
    
    def __init__(self, estimators, weights=None, n_jobs=None):
        super().__init__(estimators=estimators, weights=weights, n_jobs=n_jobs)
    
    def predict(self, X):
        """Predict class labels for X.
        
        Parameters
        ----------
        X : {array-like, sparse matrix}, shape (n_samples, n_features)
            The input samples.
            
        Returns
        -------
        predicted_labels : array-like, shape (n_samples,)
            Predicted class labels.
        """
        pred = self._predict(X)
        # Simple voting (returns the most frequent value)
        prediction = np.apply_along_axis(
            lambda x: np.argmax(np.bincount(x, weights=self._weights_not_none())),
            axis=0, arr=pred)
        return prediction


class VotingRegressor(_BaseVoting):
    """Prediction voting regressor for unfitted estimators.
    
    A voting regressor is an ensemble meta-estimator that fits base regressors 
    each on the whole dataset and then averages the predictions to form a final 
    prediction.
    
    Parameters
    ----------
    estimators : list of (string, estimator) tuples
        Invoking the ``fit`` method on the ``VotingRegressor`` will fit clones
        of those original estimators that will be stored in the class attribute
        ``self.estimators_``. An estimator can be set to `None` using
        ``set_params``.
    weights : array-like, shape (n_regressors,), optional (default=None)
        If specified, the predicted target values for each regressor are
        multiplied by the regressor weight. Uses uniform weights if None.
    n_jobs : int or None, optional (default=None)
        The number of jobs to run in parallel for ``fit``. None means 1.
    """
    
    def __init__(self, estimators, weights=None, n_jobs=None):
        super().__init__(estimators=estimators, weights=weights, n_jobs=n_jobs)
    
    def predict(self, X):
        """Predict regression target for X.
        
        Parameters
        ----------
        X : {array-like, sparse matrix}, shape (n_samples, n_features)
            The input samples.
            
        Returns
        -------
        predicted_values : array-like, shape (n_samples,)
            Predicted target values.
        """
        pred = self._predict(X)
        weights = self._weights_not_none()
        
        if weights is None:
            weights = np.ones(len(self.estimators_))
            
        avg = np.average(pred, axis=0, weights=weights)
        return avg