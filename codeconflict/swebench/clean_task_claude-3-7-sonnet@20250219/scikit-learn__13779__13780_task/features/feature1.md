# Feature 1: Allow Voting Estimator to Work with Sample Weights Even When an Estimator is None

When fitting a VotingEstimator with sample weights, we need to skip checking sample weight support for estimators that are set to None, rather than failing with an AttributeError.