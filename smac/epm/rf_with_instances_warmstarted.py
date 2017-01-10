import numpy as np
import scipy as sp
import logging

import pyrfr.regression

from smac.epm.rf_with_instances import RandomForestWithInstances


__author__ = "Marius Lindauer"
__copyright__ = "Copyright 2017, ML4AAD"
__license__ = "3-clause BSD"


class WarmstartedRandomForestWithInstances(RandomForestWithInstances):

    '''
    Interface to the random forest that takes instance features
    into account.

    Parameters
    ----------
    types: np.ndarray (D)
        Specifies the number of categorical values of an input dimension. Where
        the i-th entry corresponds to the i-th input dimension. Let say we have
        2 dimension where the first dimension consists of 3 different
        categorical choices and the second dimension is continuous than we
        have to pass np.array([2, 0]). Note that we count starting from 0.
    instance_features: np.ndarray (I, K)
        Contains the K dimensional instance features
        of the I different instances
    num_trees: int
        The number of trees in the random forest.
    do_bootstrapping: bool
        Turns on / off bootstrapping in the random forest.
    ratio_features: float
        The ratio of features that are considered for splitting.
    min_samples_split: int
        The minimum number of data points to perform a split.
    min_samples_leaf: int
        The minimum number of data points in a leaf.
    max_depth: int

    eps_purity: float

    max_num_nodes: int

    seed: int
        The seed that is passed to the random_forest_run library
        
    warmstart_models: list
        list of already trained models
    '''

    def __init__(self, types,
                 instance_features=None,
                 num_trees=10,
                 do_bootstrapping=True,
                 n_points_per_tree=0,
                 ratio_features=5. / 6.,
                 min_samples_split=3,
                 min_samples_leaf=3,
                 max_depth=20,
                 eps_purity=1e-8,
                 max_num_nodes=1000,
                 seed=42,
                 warmstart_models=None):

        RandomForestWithInstances.__init__(self, types=types, 
                                           instance_features=instance_features, 
                                           num_trees=num_trees, 
                                           do_bootstrapping=do_bootstrapping, 
                                           n_points_per_tree=n_points_per_tree, 
                                           ratio_features=ratio_features, 
                                           min_samples_split=min_samples_split, 
                                           min_samples_leaf=min_samples_leaf, 
                                           max_depth=max_depth, 
                                           eps_purity=eps_purity, 
                                           max_num_nodes=max_num_nodes, 
                                           seed=seed)
        
        self.warmstart_models = warmstart_models
        self.weights = []


    def train(self, X, y, **kwargs):
        """Trains the random forest on X and y.

        Parameters
        ----------
        X : np.ndarray [n_samples, n_features (config + instance features)]
            Input data points.
        Y : np.ndarray [n_samples, ]
            The corresponding target values.

        Returns
        -------
        self
        """
        
        super(RandomForestWithInstances,self).train(X,y)
        
        self.weights = []
        for model in self.warmstart_models:
            y_pred = model.predict(X)
            tau, _p_value = sp.stats.kendalltau(x=y, y=y_pred)
            tau = (tau + 1) /2 # scale to [0,1]; original scale [-1,1]
            self.weights.append(tau)
            
        return self

    def predict(self, X):
        """Predict means and variances for given X.

        Parameters
        ----------
        X : np.ndarray of shape = [n_samples, n_features (config + instance
        features)]

        Returns
        -------
        means : np.ndarray of shape = [n_samples, 1]
            Predictive mean
        vars : np.ndarray  of shape = [n_samples, 1]
            Predictive variance
        """
        
        weights = self.weights[:]
        weights.insert(0,1) # model at hand is fully trustworthy
        ys = []
        ys.append(super(RandomForestWithInstances,self).predict(X))
        
        for model in self.warmstart_models:
            ys.append(model.predict(X))
        means = np.array([y[0] for y in ys])
        vars = np.array([y[1] for y in ys])

        mean = np.average(means, weights=weights)
        var_of_means = np.average((means - mean)**2, weights=weights)
        var = np.average(vars, weights=weights) + var_of_means
        
        return mean, var  
        