import numpy as np

# Landsat Collection 2 Level-2 surface temperature (ST_B10): kelvin = DN * 0.00341802 + 149.0
ST_SCALE, ST_OFFSET = 0.00341802, 149.0
# QA_PIXEL bits: 0 fill, 1 dilated cloud, 2 cirrus, 3 cloud, 4 cloud shadow, 5 snow
QA_BAD = (1 << 0) | (1 << 1) | (1 << 2) | (1 << 3) | (1 << 4) | (1 << 5)


def season_for(lat):
    """Months to sample: the three hottest months outside the tropics, the whole year inside them."""
    if lat >= 23.5:
        return [6, 7, 8], "June to August"
    if lat <= -23.5:
        return [12, 1, 2], "December to February"
    return list(range(1, 13)), "all year (tropical climate)"


def to_celsius(st_dn):
    st = np.asarray(st_dn, dtype=float)
    c = st * ST_SCALE + ST_OFFSET - 273.15
    c[(st <= 0) | ~np.isfinite(st)] = np.nan
    return c


def clear_mask(qa):
    qa = np.asarray(qa).astype(np.int64)
    return (qa & QA_BAD) == 0


def hex_means(hex_of_pixel, lst_c, clear, n, min_clear=0.3):
    """Mean clear-sky temperature per hex for one scene; NaN where too little of the hex is clear."""
    h = np.asarray(hex_of_pixel).ravel()
    t = np.asarray(lst_c, dtype=float).ravel()
    ok_px = h >= 0
    tot = np.bincount(h[ok_px], minlength=n).astype(float)
    good = ok_px & np.asarray(clear).ravel() & np.isfinite(t)
    cnt = np.bincount(h[good], minlength=n).astype(float)
    s = np.bincount(h[good], weights=t[good], minlength=n)
    out = np.full(n, np.nan)
    keep = (cnt > 0) & (cnt >= min_clear * tot)
    out[keep] = s[keep] / cnt[keep]
    return out


def combine(stack, land):
    """Median over scenes of absolute temperature and of each scene's departure from its own land median.

    The departure removes day-to-day weather, so scenes from different days can be pooled."""
    stack = np.asarray(stack, dtype=float)
    land = np.asarray(land, dtype=bool)
    rel = np.full_like(stack, np.nan)
    for k in range(stack.shape[0]):
        v = stack[k][land & np.isfinite(stack[k])]
        if len(v) >= 10:
            rel[k] = stack[k] - np.median(v)
    with np.errstate(all="ignore"):
        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)
            absval = np.nanmedian(stack, axis=0)
            relval = np.nanmedian(rel, axis=0)
            nobs = np.sum(np.isfinite(rel), axis=0)
    return absval, relval, nobs
