from random import randint

import numpy as np
from numpy.core.umath_tests import inner1d

from neupy.utils import format_data
from neupy.exceptions import NotTrained
from .base import DiscreteMemory


__all__ = ('DiscreteBAM',)


def bin2sign(matrix):
    return np.where(matrix == 0, -1, 1)


def hopfield_energy(weight, X, output_data):
    return -0.5 * inner1d(X.dot(weight), output_data)


class DiscreteBAM(DiscreteMemory):
    """
    Discrete BAM Network with associations.
    Network associate every input with some target value.

    Parameters
    ----------
    {DiscreteMemory.mode}

    {DiscreteMemory.n_times}

    Methods
    -------
    train(X, output_data)
        Train network and update network weights.

    predict_output(X, n_times=None)
        Using input data recover output data. Returns two arguments.
        First is an input data, second is an output data.

    predict(X, n_times=None)
        Alias to the ``predict_output`` method.

    predict_input(output_data, n_times=None)
        Using output data recover input data. Returns two arguments.
        First is input data, second is output data.

    energy(X, output_data)
        Calculate Hopfield Energy for the input and output data.

    Notes
    -----
    - Input and output vectors should contain only binary values.

    Examples
    --------
    >>> import numpy as np
    >>> from neupy import algorithms
    >>>
    >>> zero = np.matrix([
    ...     0, 1, 1, 1, 0,
    ...     1, 0, 0, 0, 1,
    ...     1, 0, 0, 0, 1,
    ...     1, 0, 0, 0, 1,
    ...     1, 0, 0, 0, 1,
    ...     0, 1, 1, 1, 0
    ... ])
    >>>
    >>> one = np.matrix([
    ...     0, 1, 1, 0, 0,
    ...     0, 0, 1, 0, 0,
    ...     0, 0, 1, 0, 0,
    ...     0, 0, 1, 0, 0,
    ...     0, 0, 1, 0, 0,
    ...     0, 0, 1, 0, 0
    ... ])
    >>> zero.reshape((5, 6))
    >>>
    >>> half_zero = np.matrix([
    ...     0, 1, 1, 1, 0,
    ...     1, 0, 0, 0, 1,
    ...     1, 0, 0, 0, 1,
    ...     0, 0, 0, 0, 0,
    ...     0, 0, 0, 0, 0,
    ...     0, 0, 0, 0, 0,
    ... ])
    >>>
    >>> zero_hint = np.matrix([[0, 1, 0, 0]])
    >>> one_hint = np.matrix([[1, 0, 0, 0]])
    >>>
    >>> data = np.concatenate([zero, one], axis=0)
    >>> hints = np.concatenate([zero_hint, one_hint], axis=0)
    >>>
    >>> bamnet = algorithms.DiscreteBAM(mode='sync')
    >>> bamnet.train(data, hints)
    >>>
    >>> recovered_zero, recovered_hint = bamnet.predict(half_zero)
    >>> recovered_hint
    matrix([[0, 1, 0, 0]])
    >>>
    >>> zero_hint
    matrix([[0, 1, 0, 0]])
    """
    def format_predict(self, predicted_result):
        return np.where(predicted_result > 0, 1, 0).astype(int)

    def predict_input(self, output_data, n_times=None):
        output_data = format_data(output_data, is_feature1d=False)
        return self.prediction(X=None, output_data=output_data,
                               n_times=n_times)

    def predict_output(self, X, n_times=None):
        X = format_data(X, is_feature1d=False)
        return self.prediction(X=X, output_data=None,
                               n_times=n_times)

    def prediction(self, X=None, output_data=None, n_times=None):
        if self.weight is None:
            raise NotTrained("Network hasn't been trained yet")

        if X is None and output_data is not None:
            self.discrete_validation(output_data)
            output_data = bin2sign(output_data)
            X = np.sign(output_data.dot(self.weight.T))

        elif X is not None and output_data is None:
            self.discrete_validation(X)
            X = bin2sign(X)
            output_data = np.sign(X.dot(self.weight))

        else:
            raise ValueError("Prediction is possible only for input or output")

        n_output_features = output_data.shape[-1]
        n_input_features = X.shape[-1]

        if self.mode == 'async':
            if n_times is None:
                n_times = self.n_times

            for _ in range(n_times):
                input_position = randint(0, n_input_features - 1)
                output_position = randint(0, n_output_features - 1)

                X[:, input_position] = np.sign(
                    output_data.dot(self.weight[input_position, :])
                )
                output_data[:, output_position] = np.sign(
                    X.dot(self.weight[:, output_position])
                )

        return (
            self.format_predict(X),
            self.format_predict(output_data),
        )

    def train(self, X, output_data):
        self.discrete_validation(X)
        self.discrete_validation(output_data)

        output_data = bin2sign(format_data(output_data, is_feature1d=False))
        X = bin2sign(format_data(X, is_feature1d=False))

        _, wight_nrows = X.shape
        _, wight_ncols = output_data.shape
        weight_shape = (wight_nrows, wight_ncols)

        if self.weight is None:
            self.weight = np.zeros(weight_shape)

        if self.weight.shape != weight_shape:
            raise ValueError("Invalid input shapes. Number of input "
                             "features must be equal to {} and {} output "
                             "features".format(wight_nrows, wight_ncols))

        self.weight += X.T.dot(output_data)

    def energy(self, X, output_data):
        self.discrete_validation(X)
        self.discrete_validation(output_data)

        X, output_data = bin2sign(X), bin2sign(output_data)
        X = format_data(X, is_feature1d=False)
        output_data = format_data(output_data, is_feature1d=False)
        nrows, n_features = X.shape

        if nrows == 1:
            return hopfield_energy(self.weight, X, output_data)

        output = np.zeros(nrows)
        for i, rows in enumerate(zip(X, output_data)):
            output[i] = hopfield_energy(self.weight, *rows)

        return output

    predict = predict_output
