from __future__ import annotations

import numpy as np

from .background import bg_mask, bg_rv
from .smo import rv_continuous, smo, smo_rv


class SMO:
    def __init__(
        self, *, sigma: float, size: int, shape: tuple[int, ...], random_state=None
    ):
        """Wrapper to simplify the use of the Silver Mountain Operator (SMO).

        Most methods requiere a MaskedArray with saturated pixels masked. If provided
        as a non-MaskedArray, a mask is generated for the image maximum.

        Parameters
        ----------
        sigma : scalar or sequence of scalars
            Standard deviation for Gaussian kernel.
        size : int or sequence of int
            Averaging window size.
        shape : tuple of ints
            Shape of the random image used to estimate the SMO distribution.
        random_state : numpy.random.Generator
            By default, numpy.random.default_rng(seed=42).

        Notes
        -----
        Sigma and size are scale parameters,
        and should be less than the typical object size.
        """
        self.sigma = sigma
        self.size = size
        self.ndim = len(shape)
        self.smo_rv = smo_rv(shape, sigma=sigma, size=size, random_state=random_state)

    def _check_image(self, image: np.ndarray | np.ma.MaskedArray) -> np.ma.MaskedArray:
        """Checks that the image has the appropiate dimension and has a mask.

        If image is not masked, the maximum intenstiy values are masked.
        """
        if image.ndim != self.ndim:
            raise ValueError(
                f"Dimension of input image is {image.ndim}, "
                f"while this SMO was constructed for dimension {self.ndim}."
            )

        if isinstance(image, np.ma.MaskedArray):
            return image
        else:
            saturation = image.max()
            return np.ma.masked_greater_equal(image, saturation)

    def smo_image(self, image: np.ndarray | np.ma.MaskedArray) -> np.ma.MaskedArray:
        """Applies the Silver Mountain Operator (SMO) to a scalar field.

        Parameters
        ----------
        input : numpy.ndarray | np.ma.MaskedArray
            Input field.

        Returns
        -------
        np.ma.MaskedArray
        """
        image = self._check_image(image)
        return smo(image, sigma=self.sigma, size=self.size)

    def smo_probability(
        self, image: np.ndarray | np.ma.MaskedArray
    ) -> np.ma.MaskedArray:
        """Applies the Silver Mountain Operator (SMO) to a scalar field.

        Parameters
        ----------
        input : numpy.ndarray | np.ma.MaskedArray
            Input field. If there are saturated pixels, they should be masked.

        Returns
        -------
        np.ma.MaskedArray
        """
        image = self.smo_image(image)
        prob = self.smo_rv.cdf(image.data)
        return np.ma.MaskedArray(prob, image.mask)

    def bg_mask(
        self, image: np.ndarray | np.ma.MaskedArray, *, threshold: float = 0.05
    ) -> np.ma.MaskedArray:
        """Returns the input image with only SMO-chosen background pixels unmasked.

        As it is a statistical test, some foreground pixels might be included.

        Parameters
        ----------
        image : numpy.ndarray | numpy.ma.MaskedArray
            Image. If there are saturated pixels, they should be masked.
        threshold : float
            Threshold value [0, 1] for the SMO image.

        Returns
        -------
        numpy.ma.MaskedArray
        """
        image = self._check_image(image)
        return bg_mask(
            image,
            sigma=self.sigma,
            size=self.size,
            threshold=self.smo_rv.ppf(threshold),
        )

    def bg_rv(
        self, image: np.ndarray | np.ma.MaskedArray, *, threshold: float = 0.05
    ) -> rv_continuous:
        """Returns the distribution of background noise.

        It returns an instance of scipy.stats.rv_histogram.
        Use .median() to get the median value,
        or .ppf(percentile) to calculate any other desired percentile.

        Parameters
        ----------
        image : numpy.ndarray | numpy.ma.MaskedArray
            Image. If there are saturated pixels, they should be masked.
        threshold : float
            Threshold value [0, 1] for the SMO image.

        Returns
        -------
        scipy.stats.rv_continuous
        """
        image = self._check_image(image)
        return bg_rv(
            image,
            sigma=self.sigma,
            size=self.size,
            threshold=self.smo_rv.ppf(threshold),
        )

    def bg_probability(
        self, image: np.ndarray | np.ma.MaskedArray, *, threshold: float = 0.05
    ) -> np.ma.MaskedArray:
        """Returns the probability that each pixel doesn't belong to the background.

        It uses the cumulative density function (CDF) of the background distribution
        to assign a value to each pixel.

        Parameters
        ----------
        image : numpy.ndarray | numpy.ma.MaskedArray
            Image. If there are saturated pixels, they should be masked.
        threshold : float
            Threshold value [0, 1] for the SMO image.

        Returns
        -------
        np.ma.MaskedArray
            If the input has a mask, it is shared by the output.
        """
        image = self._check_image(image)
        prob = self.bg_rv(image, threshold=threshold).cdf(image.data)
        return np.ma.MaskedArray(prob, image.mask)
