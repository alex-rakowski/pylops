import logging
import warnings

import numpy as np
import scipy.fft

from pylops.signalprocessing._BaseFFTs import _BaseFFTND

logging.basicConfig(format="%(levelname)s: %(message)s", level=logging.WARNING)


class _FFTND_numpy(_BaseFFTND):
    """N-dimensional Fast-Fourier Transform using numpy"""

    def __init__(
        self,
        dims,
        dirs=(0, 1, 2),
        nffts=None,
        sampling=1.0,
        norm="ortho",
        real=False,
        ifftshift_before=False,
        fftshift_after=False,
        dtype="complex128",
    ):
        super().__init__(
            dims=dims,
            dirs=dirs,
            nffts=nffts,
            sampling=sampling,
            norm=norm,
            real=real,
            ifftshift_before=ifftshift_before,
            fftshift_after=fftshift_after,
            dtype=dtype,
        )
        if self.cdtype != np.complex128:
            warnings.warn(
                f"numpy backend always returns complex128 dtype. To respect the passed dtype, data will be casted to {self.cdtype}."
            )

        self._norm_kwargs = {"norm": None}  # backward
        if self.norm == "ortho":
            self._norm_kwargs["norm"] = "ortho"
        elif self.norm == "backward":
            self._scale = np.prod(self.nffts)
        elif self.norm == "forward":
            self._scale = 1.0 / np.prod(self.nffts)
        else:
            raise ValueError(
                f"'{self.norm}' is not one of 'ortho', 'backward' or 'forward'"
            )

    def _matvec(self, x):
        x = np.reshape(x, self.dims)
        if self.ifftshift_before.any():
            x = np.fft.ifftshift(x, axes=self.dirs[self.ifftshift_before])
        if not self.clinear:
            x = np.real(x)
        if self.real:
            y = np.fft.rfftn(x, s=self.nffts, axes=self.dirs, **self._norm_kwargs)
            # Apply scaling to obtain a correct adjoint for this operator
            y = np.swapaxes(y, -1, self.dirs[-1])
            y[..., 1 : 1 + (self.nffts[-1] - 1) // 2] *= np.sqrt(2)
            y = np.swapaxes(y, self.dirs[-1], -1)
        else:
            y = np.fft.fftn(x, s=self.nffts, axes=self.dirs, **self._norm_kwargs)
        if self.norm == "forward":
            y *= self._scale
        y = y.astype(self.cdtype)
        if self.fftshift_after.any():
            y = np.fft.fftshift(y, axes=self.dirs[self.fftshift_after])
        return y.ravel()

    def _rmatvec(self, x):
        x = np.reshape(x, self.dims_fft)
        if self.fftshift_after.any():
            x = np.fft.ifftshift(x, axes=self.dirs[self.fftshift_after])
        if self.real:
            # Apply scaling to obtain a correct adjoint for this operator
            x = x.copy()
            x = np.swapaxes(x, -1, self.dirs[-1])
            x[..., 1 : 1 + (self.nffts[-1] - 1) // 2] /= np.sqrt(2)
            x = np.swapaxes(x, self.dirs[-1], -1)
            y = np.fft.irfftn(x, s=self.nffts, axes=self.dirs, **self._norm_kwargs)
        else:
            y = np.fft.ifftn(x, s=self.nffts, axes=self.dirs, **self._norm_kwargs)
        if self.norm == "backward":
            y *= self._scale
        for direction in self.dirs:
            y = np.take(y, range(self.dims[direction]), axis=direction)
        if not self.clinear:
            y = np.real(y)
        y = y.astype(self.rdtype)
        if self.ifftshift_before.any():
            y = np.fft.fftshift(y, axes=self.dirs[self.ifftshift_before])
        return y.ravel()

    def __truediv__(self, y):
        if self.norm != "ortho":
            return self._rmatvec(y) / self._scale
        return self._rmatvec(y)


class _FFTND_scipy(_BaseFFTND):
    """N-dimensional Fast-Fourier Transform using scipy"""

    def __init__(
        self,
        dims,
        dirs=(0, 1, 2),
        nffts=None,
        sampling=1.0,
        norm="ortho",
        real=False,
        ifftshift_before=False,
        fftshift_after=False,
        dtype="complex128",
    ):
        super().__init__(
            dims=dims,
            dirs=dirs,
            nffts=nffts,
            sampling=sampling,
            norm=norm,
            real=real,
            ifftshift_before=ifftshift_before,
            fftshift_after=fftshift_after,
            dtype=dtype,
        )

        self._norm_kwargs = {"norm": None}  # backward
        if self.norm == "ortho":
            self._norm_kwargs["norm"] = "ortho"
        elif self.norm == "backward":
            self._scale = np.prod(self.nffts)
        elif self.norm == "forward":
            self._scale = 1.0 / np.prod(self.nffts)
        else:
            raise ValueError(
                f"'{self.norm}' is not one of 'ortho', 'backward' or 'forward'"
            )

    def _matvec(self, x):
        x = np.reshape(x, self.dims)
        if self.ifftshift_before.any():
            x = scipy.fft.ifftshift(x, axes=self.dirs[self.ifftshift_before])
        if not self.clinear:
            x = np.real(x)
        if self.real:
            y = scipy.fft.rfftn(x, s=self.nffts, axes=self.dirs, **self._norm_kwargs)
            # Apply scaling to obtain a correct adjoint for this operator
            y = np.swapaxes(y, -1, self.dirs[-1])
            y[..., 1 : 1 + (self.nffts[-1] - 1) // 2] *= np.sqrt(2)
            y = np.swapaxes(y, self.dirs[-1], -1)
        else:
            y = scipy.fft.fftn(x, s=self.nffts, axes=self.dirs, **self._norm_kwargs)
        if self.norm == "forward":
            y *= self._scale
        if self.fftshift_after.any():
            y = scipy.fft.fftshift(y, axes=self.dirs[self.fftshift_after])
        return y.ravel()

    def _rmatvec(self, x):
        x = np.reshape(x, self.dims_fft)
        if self.fftshift_after.any():
            x = scipy.fft.ifftshift(x, axes=self.dirs[self.fftshift_after])
        if self.real:
            # Apply scaling to obtain a correct adjoint for this operator
            x = x.copy()
            x = np.swapaxes(x, -1, self.dirs[-1])
            x[..., 1 : 1 + (self.nffts[-1] - 1) // 2] /= np.sqrt(2)
            x = np.swapaxes(x, self.dirs[-1], -1)
            y = scipy.fft.irfftn(x, s=self.nffts, axes=self.dirs, **self._norm_kwargs)
        else:
            y = scipy.fft.ifftn(x, s=self.nffts, axes=self.dirs, **self._norm_kwargs)
        if self.norm == "backward":
            y *= self._scale
        for direction in self.dirs:
            y = np.take(y, range(self.dims[direction]), axis=direction)
        if not self.clinear:
            y = np.real(y)
        if self.ifftshift_before.any():
            y = scipy.fft.fftshift(y, axes=self.dirs[self.ifftshift_before])
        return y.ravel()

    def __truediv__(self, y):
        if self.norm != "ortho":
            return self._rmatvec(y) / self._scale
        return self._rmatvec(y)


def FFTND(
    dims,
    dirs=(0, 1, 2),
    nffts=None,
    sampling=1.0,
    norm="ortho",
    real=False,
    ifftshift_before=False,
    fftshift_after=False,
    dtype="complex128",
    engine="scipy",
):
    r"""N-dimensional Fast-Fourier Transform.

    Apply N-dimensional Fast-Fourier Transform (FFT) to any n axes
    of a multi-dimensional array depending on the choice of ``dirs``.

    Using the default NumPy engine, the FFT operator is an overload to either the NumPy
    :py:func:`numpy.fft.fftn` (or :py:func:`numpy.fft.rfftn` for real models) in
    forward mode, and to :py:func:`numpy.fft.ifftn` (or :py:func:`numpy.fft.irfftn`
    for real models) in adjoint mode, or their CuPy equivalents.
    Alternatively, when the SciPy engine is chosen, the overloads are of
    :py:func:`scipy.fft.fftn` (or :py:func:`scipy.fft.rfftn` for real models) in
    forward mode, and to :py:func:`scipy.fft.ifftn` (or :py:func:`scipy.fft.irfftn`
    for real models) in adjoint mode.

    When using `real=True`, the result of the forward is also multiplied by
    :math:`\sqrt{2}` for all frequency bins except zero and Nyquist along the last
    direction of ``dirs``, and the input of the adjoint is multiplied by
    :math:`1 / \sqrt{2}` for the same frequencies.

    For a real valued input signal, it is advised to use the flag ``real=True``
    as it stores the values of the Fourier transform of the last direction at positive
    frequencies only as values at negative frequencies are simply their complex conjugates.

    Parameters
    ----------
    dims : :obj:`tuple`
        Number of samples for each dimension
    dirs : :obj:`tuple` or :obj:`int`, optional
        Direction(s) along which FFTND is applied
    nffts : :obj:`tuple` or :obj:`int`, optional
        Number of samples in Fourier Transform for each direction. In case only one
        dimension needs to be specified, use ``None`` for the other dimension in the
        tuple. The direction with None will use ``dims[dir]`` as ``nfft``. When
        supplying a tuple, the order must agree with that of ``dirs``. When a single
        value is passed, it will be used for both directions. As such the default is
        equivalent to ``nffts=(None,..., None)``.
    sampling : :obj:`tuple` or :obj:`float`, optional
        Sampling steps for each direction. When supplied a single value, it is used
        for all directions. Unlike ``nffts``, ``None``s will not be converted to the
        default value.
    norm : `{"ortho", "backward", "forward"}`, optional
        * "ortho": Scales forward and adjoint FFT transforms with :math:`1/\sqrt{N_F}`,
        where :math:`N_F` is the number of samples in the Fourier domain given by
        product of all elements of ``nffts``.
        * "backward": Does not scale the forward or the adjoint FFT transforms. Note
        that the adjoint behaviour of this option differs from :py:func:`ifftn`
        implementations in NumPy and SciPy.
        * "forward": Scales both the forward and adjoint FFT transforms by
        :math:`1/N_F`. Note the forward behaviour of this option differs from
        :py:func:`fftn` implementations in NumPy and SciPy.
        Also note that for "forward" and "backward", the operator is not unitary,
        that is, the adjoint is not the inverse. To invert the operator, simply use
        `Op \ y`.
    real : :obj:`bool`, optional
        Model to which fft is applied has real numbers (``True``) or not
        (``False``). Used to enforce that the output of adjoint of a real
        model is real. Note that the real FFT is applied only to the first
        dimension to which the FFTND operator is applied (last element of
        ``dirs``)
    ifftshift_before : :obj:`tuple` or :obj:`bool`, optional
        Apply ifftshift (``True``) or not (``False``) to model vector (before FFT).
        Consider using this option when the model vector's respective axis is symmetric
        with respect to the zero value sample. This will shift the zero value sample to
        coincide with the zero index sample. With such an arrangement, FFT will not
        introduce a sample-dependent phase-shift when compared to the continuous Fourier
        Transform.
        When passing a single value, the shift will the same for every direction. Pass
        a tuple to specify which dimensions are shifted.
    fftshift_after : :obj:`tuple` or :obj:`bool`, optional
        Apply fftshift (``True``) or not (``False``) to data vector (after FFT).
        Consider using this option when you require frequencies to be arranged
        naturally, from negative to positive. When not applying fftshift after FFT,
        frequencies are arranged from zero to largest positive, and then from negative
        Nyquist to the frequency bin before zero.
        When passing a single value, the shift will the same for every direction. Pass
        a tuple to specify which dimensions are shifted.
    engine : :obj:`str`, optional
        Engine used for fft computation (``numpy`` or ``scipy``).
    dtype : :obj:`str`, optional
        Type of elements in input array. Note that the ``dtype`` of the operator
        is the corresponding complex type even when a real type is provided.
        In addition, note that the NumPy backend does not support returning ``dtype``s
        different than ``complex128``. As such, when using the NumPy backend, arrays will
        be force-casted to types corresponding to the supplied ``dtype``.
        The SciPy backend supports all precisions natively.
        Under both backends, when a real ``dtype`` is supplied, a real result will be
        enforced on the result of the ``rmatvec`` and the input of the ``matvec``.

    Attributes
    ----------
    dims_fft : :obj:`tuple`
        Shape of the array after the forward, but before linearization. E.g.
        ``y_reshaped = (Op * x.ravel()).reshape(Op.dims_fft)``.
    fs : :obj:`tuple`
        Each element of the tuple corresponds to the Discrete Fourier Transform
        sample frequencies along the respective direction given by ``dirs``.
    real : :obj:`bool`
        When True, uses ``rfftn``/``irfftn``
    rdtype : :obj:`bool`
        Expected input type to the forward
    cdtype : :obj:`bool`
        Output type of the forward. Complex equivalent to ``rdtype``.
    shape : :obj:`tuple`
        Operator shape
    clinear : :obj:`bool`
        Operator is complex-linear. Is false when either ``real=True`` or when
        ``dtype`` is not a complex type.
    explicit : :obj:`bool`
        Operator contains a matrix that can be solved explicitly
        (True) or not (False)

    Raises
    ------
    ValueError
        If ``nffts`` or ``sampling`` are not either a single value or tuple with
        the same dimension ``dirs``.
    NotImplementedError
        If ``engine`` is neither ``numpy``, nor ``scipy``.

    Notes
    -----
    The FFTND operator applies the N-dimensional forward Fourier transform
    to a multi-dimensional array. Considering an N-dimensional signal
    :math:`d(x_1, \ldots, x_N)`.
    The FFTND in forward mode is:

    .. math::
        D(k_1, \ldots, k_N) = \mathscr{F} (d) = \frac{1}{\sqrt{N_F}} \int \int
        d(x_1, \ldots, x_N)
        e^{-j2\pi k_1 x_1} \cdots
        e^{-j 2 \pi k_N x_N}  dx_1 \cdots dx_N

    Similarly, the  three-dimensional inverse Fourier transform is applied to
    the Fourier spectrum :math:`D(k_z, k_y, k_x)` in adjoint mode:

    .. math::
        d(x_1, \ldots, x_N) = \mathscr{F}^{-1} (D) = \sqrt{N_F}  \int \int
        D(k_1, \ldots, k_N)
        e^{-j2\pi k_1 x_1} \cdots
        e^{-j 2 \pi k_N x_N} dk_1 \cdots  dk_N

    where :math:`N_F` is the number of samples in the Fourier domain given by the
    product of the element of ``nffts``.
    Both operators are effectively discretized and solved by a fast iterative
    algorithm known as Fast Fourier Transform. Note that the FFTND operator
    (using `norm="ortho"`) is a special operator in that the adjoint is also
    the inverse of the forward mode. For other norms, this does not hold (see ``norm``
    help). However, for any norm, the N-dimensional Fourier transform is Hermitian
    for real input signals.

    """

    if engine == "numpy":
        f = _FFTND_numpy(
            dims=dims,
            dirs=dirs,
            nffts=nffts,
            sampling=sampling,
            norm=norm,
            real=real,
            ifftshift_before=ifftshift_before,
            fftshift_after=fftshift_after,
            dtype=dtype,
        )
    elif engine == "scipy":
        f = _FFTND_scipy(
            dims=dims,
            dirs=dirs,
            nffts=nffts,
            sampling=sampling,
            norm=norm,
            real=real,
            ifftshift_before=ifftshift_before,
            fftshift_after=fftshift_after,
            dtype=dtype,
        )
    else:
        raise NotImplementedError("engine must be numpy or scipy")
    return f
