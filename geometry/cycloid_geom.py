"""
cycloid_geom.py - numpy-only 2D geometry for the NEMA17 cycloidal drive.
Runs inside Blender's bundled Python (numpy is included) or plain CPython.

All units mm. Z is the drive axis. Profiles are closed 2D polylines (no repeated
last point), counter-clockwise, centred on their own axis.

    python cycloid_geom.py            # writes disc_profile.csv, ring_inner_profile.csv, prints checks
"""
import numpy as np

# ---- default parameters come from params.py (single source of truth); fallbacks match it
try:
    from params import N_PINS, R_PIN, RP, E, C_PROF, C_WALL
except ImportError:
    N_PINS, R_PIN, RP, E, C_PROF, C_WALL = 16, 25.0, 1.5, 1.2, 0.10, 0.40

def disc_profile(N=N_PINS, R=R_PIN, rp=RP, e=E, c=C_PROF, n=1800):
    """Cycloidal disc outline in the disc frame (N-1 lobes).
    Equidistant curve of the epitrochoid at distance rp + c."""
    t = np.linspace(0.0, 2*np.pi, n, endpoint=False)
    psi = np.arctan2(np.sin((1-N)*t), R/(e*N) - np.cos((1-N)*t))
    r = rp + c
    x = R*np.cos(t) - r*np.cos(t + psi) - e*np.cos(N*t)
    y = -R*np.sin(t) + r*np.sin(t + psi) + e*np.sin(N*t)
    p = np.c_[x, y]
    if _signed_area(p) < 0:           # force CCW
        p = p[::-1]
    return p


def disc_pose(theta, e=E, N=N_PINS, phase=0.0):
    """World pose of a disc for input (cam) angle theta [rad].
    Returns (centre_xy, rotation_rad). Disc B uses phase=pi and is the SAME part rotated 180 deg."""
    centre = e*np.array([np.cos(theta + phase), np.sin(theta + phase)])
    rot = -theta/(N-1) + phase
    return centre, rot


def ring_inner_profile(N=N_PINS, R=R_PIN, rp=RP, e=E, c=C_PROF, gap=C_WALL, nb=1440, pin_seg=96):
    """Inner outline of the ring-pin housing = (swept disc envelope + gap) with the
    pin circles added back as solid. Returned as a star-shaped polar polyline."""
    p = disc_profile(N, R, rp, e, c, n=1500)
    rmax = np.zeros(nb)
    for th in np.linspace(0, 2*np.pi, 1441):
        ctr, a = disc_pose(th, e, N)
        ca, sa = np.cos(a), np.sin(a)
        q = p @ np.array([[ca, sa], [-sa, ca]]) + ctr
        ang = np.arctan2(q[:, 1], q[:, 0]) % (2*np.pi)
        b = (ang/(2*np.pi)*nb).astype(int) % nb
        np.maximum.at(rmax, b, np.hypot(q[:, 0], q[:, 1]))
    # widen by one bin each side so binning never under-cuts the envelope
    rmax = np.maximum(rmax, np.maximum(np.roll(rmax, 1), np.roll(rmax, -1))) + gap
    phi = (np.arange(nb) + 0.5)/nb*2*np.pi
    # pin near-side along each ray (solid pins win over the relief)
    pitch = 2*np.pi/N
    d = (phi + pitch/2) % pitch - pitch/2           # angle to nearest pin
    s = R*np.sin(d)
    inside = np.abs(s) < rp
    pin_r = np.where(inside, R*np.cos(d) - np.sqrt(np.clip(rp**2 - s**2, 0, None)), np.inf)
    r = np.minimum(rmax, pin_r)
    return np.c_[r*np.cos(phi), r*np.sin(phi)]


def _signed_area(p):
    x, y = p[:, 0], p[:, 1]
    return 0.5*np.sum(x*np.roll(y, -1) - np.roll(x, -1)*y)


def summary(N=N_PINS, R=R_PIN, rp=RP, e=E, c=C_PROF):
    d = disc_profile(N, R, rp, e, c)
    rr = np.hypot(d[:, 0], d[:, 1])
    ring = ring_inner_profile(N, R, rp, e, c)
    rw = np.hypot(ring[:, 0], ring[:, 1])
    return dict(lobes=N-1, ratio=f"{N-1}:1 (output reverses)", k=e*N/R,
                disc_r_min=rr.min(), disc_r_max=rr.max(),
                ring_r_min=rw.min(), ring_r_max=rw.max())


if __name__ == "__main__":
    np.savetxt("disc_profile.csv", disc_profile(), delimiter=",", fmt="%.5f", header="x_mm,y_mm", comments="")
    np.savetxt("ring_inner_profile.csv", ring_inner_profile(), delimiter=",", fmt="%.5f", header="x_mm,y_mm", comments="")
    for k, v in summary().items():
        print(f"{k:12s} {v:.3f}" if isinstance(v, float) else f"{k:12s} {v}")
