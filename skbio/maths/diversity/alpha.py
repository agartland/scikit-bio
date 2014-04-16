#!/usr/bin/env python
r"""
Alpha diversity measures (:mod:`skbio.maths.diversity.alpha`)
=============================================================

.. currentmodule:: skbio.maths.diversity.alpha

This module provides implementations of various alpha diversity measures.

Functions
---------

.. autosummary::
   :toctree: generated/

   observed_species

"""
from __future__ import division

# ----------------------------------------------------------------------------
# Copyright (c) 2013--, scikit-bio development team.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file COPYING.txt, distributed with this software.
# ----------------------------------------------------------------------------

import numpy as np
from scipy.special import gammaln


def ace(count, rare_threshold=10):
    """Implements the ACE metric from EstimateS. Based on the equations
    given under ACE:Abundance-based Coverage Estimator.

    count = an OTU by sample vector
    rare_threshold = threshold at which a species containing as many or
    fewer individuals will be considered rare.

    IMPORTANT NOTES:

    Raises a value error if every rare species is a singleton.

    if no rare species exist, just returns the number of abundant species

    rare_threshold default value is 10. Based on Chao 2000 in Statistica
    Sinica pg. 229 citing empirical observations by Chao, Ma, Yang 1993.

    If the count vector contains 0's, indicating species which are known
    to exist in the environment but did not appear in the sample, they
    will be ignored for the purpose of calculating s_rare."""

    def frequency_counter(count):
        """Creates a frequency count array to beused by every other function."""
        return _indices_to_counts(count)

    def species_rare(freq_counts, rare_threshold):
        """freq_counts number of rare species. Default value of rare is 10 or
        fewer individuals. Based on Chao 2000 in Statistica Sinica pg. 229
        citing empirical observations by Chao, Ma and Yang in 1993."""
        return freq_counts[1:rare_threshold + 1].sum()

    def species_abundant(freq_counts, rare_threshold):
        """freq_counts number of abundant species. Default value of abundant is
        greater than 10 individuals. Based on Chao 2000 in Statistica Sinica
        pg.229  citing observations by Chao, Ma and Yang in 1993."""
        return freq_counts[rare_threshold + 1:].sum()

    def number_rare(freq_counts, gamma=False):
        """Number of individuals in rare species. gamma=True generates the
        n_rare used for the variation coefficient."""
        n_rare = 0
        if gamma:
            for i, j in enumerate(freq_counts[:rare_threshold + 1]):
                n_rare = n_rare + (i * j) * (i - 1)
            return n_rare

        for i, j in enumerate(freq_counts[:rare_threshold + 1]):
            n_rare = n_rare + (i * j)
        return n_rare

    # calculations begin

    freq_counts = frequency_counter(count)

    if freq_counts[1:rare_threshold].sum() == 0:
        return species_abundant(freq_counts, rare_threshold)

    if freq_counts[1] == freq_counts[1:rare_threshold].sum():
        raise ValueError("The only rare species are singletons, so the ACE "
                         "metric is undefined. EstimateS suggests using "
                         "bias-corrected Chao1 instead.")

    s_abun = species_abundant(freq_counts, rare_threshold)

    s_rare = species_rare(freq_counts, rare_threshold)

    n_rare = number_rare(freq_counts)

    c_ace = 1 - (freq_counts[1]).sum() / float(n_rare)

    top = s_rare * number_rare(freq_counts, gamma=True)
    bottom = c_ace * n_rare * (n_rare - 1.0)

    gamma_ace = (top / bottom) - 1.0

    if 0 > gamma_ace:
        gamma_ace = 0

    return s_abun + (s_rare / c_ace) + ((freq_counts[1] / c_ace) * gamma_ace)


def berger_parker_d(counts):
    """Fraction of the sample that belongs to the most abundant species.

    References
    ----------
    .. [1] Berger & Parker 1970, by way of SDR-IV online help.

    """
    return counts.max() / counts.sum()


def brillouin_d(counts):
    """Calculate Brilloun index of alpha diversity.

    References
    ----------
    .. [1] Pielou 1975, by way of SDR-IV.

    """
    nz = counts[counts.nonzero()]
    n = nz.sum()
    return (gammaln(n + 1) - gammaln(nz + 1).sum()) / n


def chao1(counts, bias_corrected=True):
    """Calculates chao1 according to table in EstimateS manual.

    Specifically, uses bias-corrected version unless bias_corrected is set
    to False _and_ there are both singletons and doubletons.

    Uncorrected:

    Calculates chao1 given counts. Eq. 1 in EstimateS manual.

    Formula: chao1 = S_obs + N_1^2/(2*N_2) where N_1 and N_2 are
    count of singletons and doubletons respectively.

    Note: this is the original formula from Chao 1984, not bias-corrected,
    and is Equation 1 in the EstimateS manual.

    Corrected:

    Calculates bias-corrected chao1 given counts: Eq. 2 in EstimateS manual.

    Formula: chao1 = S_obs + N_1(N_1-1)/(2*(N_2+1)) where N_1 and N_2 are
    count of singletons and doubletons respectively.

    Note: this is the bias-corrected formulat from Chao 1987, Eq. 2 in the
    EstimateS manual.

    """
    o, s, d = osd(counts)

    if not bias_corrected and s and d:
        return o + s ** 2 / (d * 2)
    else:
        return o + s * (s - 1) / (2 * (d + 1))


def chao1_confidence(counts, bias_corrected=True, zscore=1.96):
    """Returns chao1 confidence (lower, upper) from counts."""
    o, s, d = osd(counts)
    if s:
        chao = chao1(counts, bias_corrected)
        chaovar = _chao1_var(counts, bias_corrected)
        return _chao_confidence_with_singletons(chao, o, chaovar, zscore)
    else:
        n = counts.sum()
        return _chao_confidence_no_singletons(n, o, zscore)


def _chao1_var_uncorrected(singles, doubles):
    """Calculates chao1, uncorrected.

    From EstimateS manual, equation 5.
    """
    r = float(singles) / doubles
    return doubles * (.5 * r ** 2 + r ** 3 + .24 * r ** 4)


def _chao1_var_bias_corrected(singles, doubles):
    """Calculates chao1 variance, bias-corrected.

    From EstimateS manual, equation 6.
    """
    s, d = float(singles), float(doubles)
    return s * (s - 1) / (2 * (d + 1)) + (s * (2 * s - 1) ** 2) / (4 * (d + 1) ** 2) + \
        (s ** 2 * d * (s - 1) ** 2) / (4 * (d + 1) ** 4)


def _chao1_var_no_doubletons(singles, chao1):
    """Calculates chao1 variance in absence of doubletons.

    From EstimateS manual, equation 7.

    chao1 is the estimate of the mean of Chao1 from the same dataset.
    """
    s = float(singles)
    return s * (s - 1) / 2 + s * (2 * s - 1) ** 2 / 4 - s ** 4 / (4 * chao1)


def _chao1_var_no_singletons(n, observed):
    """Calculates chao1 variance in absence of singletons. n = # individuals.

    From EstimateS manual, equation 8.
    """
    o = float(observed)
    return o * np.exp(-n / o) * (1 - np.exp(-n / o))


def _chao1_var(counts, bias_corrected=True):
    """Calculates chao1 variance using decision rules in EstimateS."""
    o, s, d = osd(counts)
    if not d:
        c = chao1(counts, bias_corrected)
        return _chao1_var_no_doubletons(s, c)
    if not s:
        n = counts.sum()
        return _chao1_var_no_singletons(n, o)
    if bias_corrected:
        return _chao1_var_bias_corrected(s, d)
    else:
        return _chao1_var_uncorrected(s, d)


def _chao_confidence_with_singletons(chao, observed, var_chao, zscore=1.96):
    """Calculates confidence bounds for chao1 or chao2.

    Uses Eq. 13 of EstimateS manual.

    zscore = score to use for confidence, default = 1.96 for 95% confidence.
    """
    T = float(chao - observed)
    # if no diff betweeh chao and observed, CI is just point estimate of
    # observed
    if T == 0:
        return observed, observed
    K = np.exp(abs(zscore) * np.sqrt(np.log(1 + (var_chao / T ** 2))))
    return observed + T / K, observed + T * K


def _chao_confidence_no_singletons(n, observed, zscore=1.96):
    """Calculates confidence bounds for chao1/chao2 in absence of singletons.

    Uses Eq. 14 of EstimateS manual.

    n = number of individuals, observed = number of species.
    """
    s = float(observed)
    P = np.exp(-n / s)
    return max(s, s / (1 - P) - zscore * np.sqrt((s * P / (1 - P)))), \
        s / (1 - P) + zscore * np.sqrt(s * P / (1 - P))


def dominance(counts):
    """Calculate probability that two species sampled are the same.

    Dominance = 1 - Simpson's index, sum of squares of probabilities.

    """
    freqs = counts / counts.sum()
    return (freqs * freqs).sum()


def doubles(counts):
    """Return count of double occurrences."""
    return (counts == 2).sum()


def enspie(counts):
    """Calculate ENS_pie alpha diversity measure.

    ENS_pie = 1 / sum(pi ^ 2) with the sum occurring over all ``S`` species in
    the pool. ``pi`` is the proportion of the entire community that species
    ``i`` represents.

    Notes
    -----
    For more information about ENS_pie, see [1]_.

    References
    ----------
    .. [1] "Scale-dependent effect sizes of ecological drivers on biodiversity:
       why standardised sampling is not enough". Chase and Knight. Ecology
       Letters, Volume 16, Issue Supplement s1, pgs 17-26 May 2013.

    """
    return 1 / dominance(counts)

# For backwards-compatibility with QIIME.
simpson_reciprocal = enspie


def equitability(counts, base=2):
    """Calculate Shannon index corrected for number of species, pure evenness.

    """
    numerator = shannon(counts, base)
    denominator = np.log(observed_species(counts)) / np.log(base)
    return numerator / denominator


def esty_ci(counts):
    """Esty's CI for (1-m).

    counts: Vector of counts (NOT the sample)

    Esty's CI is defined in
    Esty WW (1983) A Normal limit law for a nonparametric estimator of the
    coverage of a random sample. Ann Statist 11: 905-912.

    n1 / n  +/- z * square-root(W);

    where
    n1 = number of species observed once in n samples;
    n = sample size;
    z = a constant that depends on the targeted confidence and based on
        the Normal distribution. For a 95% CI, z=1.959963985;
    n2 = number of species observed twice in n samples;
    W = [ n1*(n - n1)  +  2*n*n2 ] / (n**3).

    Note: for other confidence levels we first need the appropriate z,
          Not yet hooked up to CLI.

    Returns: (upper bound, lower bound)
    """
    n1 = singles(counts)
    n2 = doubles(counts)
    n = counts.sum()
    z = 1.959963985
    W = (n1 * (n - n1) + 2 * n * n2) / (n ** 3)

    return n1 / n + z * np.sqrt(W), n1 / n - z * np.sqrt(W)


def gini_index(data, method='rectangles'):
    """Calculates the gini index of data.
    Notes:
     formula is G = A/(A+B) where A is the area between y=x and the Lorenz curve
     and B is the area under the Lorenz curve. Simplifies to 1-2B since A+B=.5
     Formula available on wikipedia.
    Inputs:
     data - list or 1d arr, counts/abundances/proportions etc. All entries must
     be non-negative.
     method - str, either 'rectangles' or 'trapezoids'. see
     lorenz_curve_integrator for details.
    """
    lorenz_points = _lorenz_curve(data)
    B = _lorenz_curve_integrator(lorenz_points, method)
    return 1 - 2 * B


def goods_coverage(counts):
    """Return Good's Coverage of counts.

    C = 1 - (n1/N)
    n1 = number of OTUs with abundance of 1
    N = number of individuals (sum of abundances for all OTUs)

    """
    n1 = (np.asarray(counts) == 1).sum()
    N = (np.asarray(counts)).sum()
    return 1 - (n1 / N)


def heip_e(counts):
    """Calculate Heip's evenness measure.

    References
    ----------
    .. [1] Heip & Engels 1974.

    """
    return (np.exp(shannon(counts, base=np.e) - 1) /
            (observed_species(counts) - 1))


def kempton_taylor_q(counts, lower_quantile=.25, upper_quantile=.75):
    """Kempton-Taylor (1976) q index of alpha diversity, by way of SDR-IV.

    Estimates the slope of the cumulative abundance curve in the interquantile
    range. By default, uses lower and upper quartiles, rounding inwards.

    Note: this differs slightly from the results given in Magurran 1998.
    Specifically, we have 14 in the numerator rather than 15. Magurran
    recommends counting half of the species with the same # counts as the
    point where the UQ falls and the point where the LQ falls, but the
    justification for this is unclear (e.g. if there were a very large #
    species that just overlapped one of the quantiles, the results would
    be considerably off). Leaving the calculation as-is for now, but consider
    changing.
    """
    n = len(counts)
    lower = int(np.ceil(n * lower_quantile))
    upper = int(n * upper_quantile)
    sorted_counts = np.sort(counts)
    return (upper - lower) / np.log(sorted_counts[upper] /
                                    sorted_counts[lower])


def margalef(counts):
    """Margalef's index, assumes log accumulation.

    References
    ----------
    Magurran 2004, p 77.

    """
    return (observed_species(counts) - 1) / np.log(counts.sum())


def mcintosh_d(counts):
    """Calculate McIntosh index of alpha diversity.

    References
    ----------
    .. [1] McIntosh 1967, by way of SDR-IV.

    """
    u = np.sqrt((counts * counts).sum())
    n = counts.sum()
    return (n - u) / (n - np.sqrt(n))


def mcintosh_e(counts):
    """Calculate McIntosh's evenness measure.

    References
    ----------
    .. [1] Heip & Engels 1974 p 560 (wrong in SDR-IV).

    """
    numerator = np.sqrt((counts * counts).sum())
    n = counts.sum()
    s = observed_species(counts)
    denominator = np.sqrt((n - s + 1) ** 2 + s - 1)
    return numerator / denominator


def menhinick(counts):
    """Menhinick's index, assumes sqrt accumulation.

    References
    ----------
    .. [1] Magurran 2004, p 77.

    """
    return observed_species(counts) / np.sqrt(counts.sum())


def observed_species(counts):
    """Calculate number of distinct species."""
    return (counts != 0).sum()


def osd(counts):
    """Calculate **o**bserved, **s**ingles and **d**oubles from counts."""
    return observed_species(counts), singles(counts), doubles(counts)


def robbins(counts):
    """Robbins 1968 estimator for Pr(unobserved) at n trials.

    probability_of_unobserved_colors = S/(n+1),

    Notes
    -----
    This is the estimate for ``(n-1)`` counts, i.e. x-axis is off by 1.

    References
    ----------
    .. [1] H. E. Robbins (1968, Ann. of Stats. Vol 36, pp. 256-257)
    (where s = singletons).

    """
    return singles(counts) / counts.sum()


def shannon(counts, base=2):
    """Calculate Shannon entropy of counts, default in bits."""
    freqs = counts / counts.sum()
    nonzero_freqs = freqs[freqs.nonzero()]
    return -(nonzero_freqs * np.log(nonzero_freqs)).sum() / np.log(base)


def simpson(counts):
    """Calculate Simpson's index.

    Simpson's index = 1 - dominance.

    """
    return 1 - dominance(counts)


def simpson_e(counts):
    """Calculate Simpson's evenness."""
    return enspie(counts) / observed_species(counts)


def singles(counts):
    """Return count of single occurrences."""
    return (counts == 1).sum()


def strong(counts):
    """Calculate Strong's 2002 dominance index, by way of SDR-IV."""
    n = counts.sum()
    s = observed_species(counts)
    i = np.arange(1, len(counts) + 1)
    sorted_sum = np.sort(counts)[::-1].cumsum()
    return (sorted_sum / n - (i / s)).max()


def _indices_to_counts(indices, result=None):
    """Converts vector of indices to counts of each index.

    WARNING: does not check that 'result' array is big enough to store new
    counts, suggest preallocating based on whole dataset if doing cumulative
    analysis.

    """
    if result is None:
        max_val = indices.max()
        result = np.zeros(max_val + 1)
    for i in indices:
        result[i] += 1
    return result


def _lorenz_curve(data):
    """Calculates the Lorenz curve for input data.
    Notes:
     Formula available on wikipedia.
    Inputs:
     data - list or 1d arr, counts/abundances/proportions etc. All entries must
     be non-negative."""
    if any(np.array(data) < 0):
        raise ValueError('Lorenz curves aren\'t meaningful for non-positive ' +
                         'data.')
    # dont wan't to change input, copy and sort
    sdata = np.array(sorted((data[:])))
    n = float(len(sdata))
    Sn = sdata.sum()
    # ind+1 because must sum first point, eg. x[:0] = []
    lorenz_points = [((ind + 1) / n, sdata[:ind + 1].sum() / Sn)
                     for ind in range(int(n))]
    return lorenz_points


def _lorenz_curve_integrator(lc_pts, method):
    """Calculates the area under a lorenz curve.
    Notes:
     Could be utilized for integrating other simple, non-pathological
     'functions' where width of the trapezoids is constant.
     Two methods are available.
     1. Trapezoids, connecting the lc_pts by linear segments between them.
        Basically assumes that given sampling is accurate and that more features
        of given data would fall on linear gradients between the values of this
        data. formula is: dx[(h_0+h_n)/2 + sum(i=1,i=n-1,h_i)]
     2. Rectangles, connecting lc_pts by lines parallel to x axis. This is the
        correct method in my opinion though trapezoids might be desirable in
        some circumstances. forumla is : dx(sum(i=1,i=n,h_i))
    Inputs:
     lc_pts - list of tuples, output of lorenz_curve.
     method - str, either 'rectangles' or 'trapezoids'
    """
    if method is 'trapezoids':
        dx = 1. / len(lc_pts)  # each point differs by 1/n
        h_0 = 0.0  # 0 percent of the population has zero percent of the goods
        h_n = lc_pts[-1][1]
        sum_hs = sum([pt[1] for pt in lc_pts[:-1]])  # the 0th entry is at x=
        # 1/n
        return dx * ((h_0 + h_n) / 2. + sum_hs)
    elif method is 'rectangles':
        dx = 1. / len(lc_pts)  # each point differs by 1/n
        return dx * sum([pt[1] for pt in lc_pts])
    else:
        raise ValueError("Method '%s' not implemented. Available methods: "
                         "'rectangles', 'trapezoids'." % method)
