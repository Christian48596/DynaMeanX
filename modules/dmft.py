#!/usr/bin/env python3
"""
A Python module that replicates the original DMFT shell script +
embedded Mathematica logic. Performs:

1) Copies Delta.dat -> Delta.dat.prev (if Delta.dat exists)
2) Reads resigma.dat (Re(sigma)) and imsigma.dat (Im(sigma)) => sigma(omega)
3) Defines htDOS(...) and computes G_loc, A(omega)
4) Writes G_loc.dat, imaw.dat, reaw.dat
5) Computes new Delta.dat from G_loc, sigma
6) Calls "kk Delta.dat Delta-re.dat" at the end
7) Finally, solves for chemical potential mu such that integrated spectral
   function = n_target, using user-provided mu_min, mu_max, and max_iter.

It plots, in real time, the convergence of:
   - F(mu) = n(mu) - n_target
   - mu
vs. iteration, and closes the plot at the end,
saving a unique PDF file to avoid overwriting.
"""

import os
import math
import cmath
import shutil
import subprocess
import logging
import matplotlib
matplotlib.use('TkAgg')  # or 'QtAgg' if you want a live window
import matplotlib.pyplot as plt
from datetime import datetime

from .parameter_parser import get_parameters

class DMFTError(Exception):
    """Custom exception for errors in dmft.py."""
    pass

# -------------------------------------------------------------------
# Configure logger for this module
# -------------------------------------------------------------------
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

if not logger.handlers:
    # File Handler captures all logs (DEBUG+) in dmft.log
    fh = logging.FileHandler('dmft.log')
    fh.setLevel(logging.DEBUG)
    fh_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    fh.setFormatter(fh_formatter)
    logger.addHandler(fh)

    # Console Handler only shows INFO+ (errors/warnings) on screen
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    ch_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    ch.setFormatter(ch_formatter)
    logger.addHandler(ch)

logger.propagate = False


def _read_two_column_data(filename):
    """Read 2-col text (omega, value)."""
    data = []
    try:
        with open(filename, 'r') as f:
            for line in f:
                line = line.strip()
                if (not line) or line.startswith('#'):
                    continue
                parts = line.split()
                if len(parts) >= 2:
                    x = float(parts[0])
                    y = float(parts[1])
                    data.append((x, y))
    except FileNotFoundError:
        raise DMFTError(f"{filename} not found.")
    except Exception as e:
        raise DMFTError(f"Error reading {filename}: {e}")
    return data

def _write_two_column_data(filename, data):
    """Write list of (omega, value) to text file."""
    try:
        with open(filename, 'w') as f:
            for (x, y) in data:
                f.write(f"{x} {y}\n")
    except Exception as e:
        raise DMFTError(f"Error writing {filename}: {e}")


def fermi_dirac(omega, mu, T):
    """Fermi–Dirac distribution."""
    if T < 1e-12:
        return 1.0 if (omega - mu) < 0 else 0.0
    exponent = (omega - mu) / T
    if exponent > 40.0:
        return 0.0
    elif exponent < -40.0:
        return 1.0
    return 1.0 / (math.exp(exponent) + 1.0)

def compute_occupation(mu, A_data, T):
    """Trapezoidal integration of A(omega)*f(omega,mu,T)."""
    if len(A_data) < 2:
        return 0.0
    occ = 0.0
    for i in range(len(A_data)-1):
        w1, A1 = A_data[i]
        w2, A2 = A_data[i+1]
        f1 = fermi_dirac(w1, mu, T)
        f2 = fermi_dirac(w2, mu, T)
        dw = (w2 - w1)
        occ += 0.5*(A1*f1 + A2*f2)*dw
    return occ


def find_mu_for_occupation(A_data, n_target, T, eps_n, mu_min, mu_max, max_iter, iteration_label=None):
    """
    Bisection to find mu s.t. n(mu) = n_target.
    Also shows a live, iteration-by-iteration plot of:
      - F(mu) = n(mu) - n_target
      - mu

    iteration_label: optional string to embed in output filename
    """

    plt.ion()

    # Create figure, subplots
    fig, (axF, axMu) = plt.subplots(2, 1, figsize=(6, 8))
    fig.suptitle(r'$\mathrm{Real\!-\!time\ Bisection\ Convergence}$')

    iters = []
    fvals = []  # F(mu_i) = n(mu_i) - n_target
    mus   = []

    lineF, = axF.plot([], [], 'o-b', label=r'$F(\mu_i)\!=\!n(\mu_i)-n_{\mathrm{target}}$')
    lineM, = axMu.plot([], [], 'o-r', label=r'$\mu_i$')

    axF.axhline(0.0, color='k', ls='--', lw=0.8)
    axF.set_xlabel(r'$\mathrm{Iteration}$')
    axF.set_ylabel(r'$F(\mu) = n(\mu) - n_{\mathrm{target}}$')
    axF.grid(True)
    axF.legend()

    axMu.set_xlabel(r'$\mathrm{Iteration}$')
    axMu.set_ylabel(r'$\mu$')
    axMu.grid(True)
    axMu.legend()

    f_min = compute_occupation(mu_min, A_data, T) - n_target
    f_max = compute_occupation(mu_max, A_data, T) - n_target
    converged = False
    mu_mid = 0.5*(mu_min + mu_max)
    f_mid = None

    iteration_data = []

    for i in range(max_iter):
        mu_mid = 0.5*(mu_min + mu_max)
        occ_mid = compute_occupation(mu_mid, A_data, T)
        f_mid = occ_mid - n_target

        iteration_data.append((i, mu_mid, f_mid))

        iters.append(i)
        mus.append(mu_mid)
        fvals.append(f_mid)

        lineF.set_data(iters, fvals)
        lineM.set_data(iters, mus)

        axF.relim()
        axF.autoscale_view()
        axMu.relim()
        axMu.autoscale_view()

        plt.draw()
        plt.pause(0.5)

        # check convergence
        if abs(f_mid) < eps_n:
            converged = True
            break

        # bisection step
        if f_min * f_mid > 0.0:
            mu_min = mu_mid
            f_min  = f_mid
        else:
            mu_max = mu_mid
            f_max  = f_mid

    # Generate a unique filename so we don't overwrite previous PDFs
    if iteration_label is not None:
        out_pdf = f"bisection_convergence_step_{iteration_label}.pdf"
    else:
        # fallback to timestamp-based approach
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        out_pdf = f"bisection_convergence_{timestamp}.pdf"

    plt.savefig(out_pdf)
    logger.info(f"Bisection convergence plot saved to '{out_pdf}'")
    plt.close(fig)

    if not converged:
        logger.warning(f"Bisection did not converge after {max_iter} iterations.")

    return mu_mid, f_mid, converged, iteration_data


def execute_dmft(iteration_index=None):
    """
    Main routine that does:
     - read parameters
     - compute spectral function, G_loc
     - do the bisection for mu (with real-time plot)
     - close the plot at the end

    iteration_index: optional integer or string. If provided, we embed
                     it in the bisection PDF filename to avoid overwriting.
    """

    logger.debug("Starting DMFT steps (execute_dmft).")

    params = get_parameters()
    n_target    = params["n_target"]
    T           = params["T"]
    eps_n       = params["eps_n"]
    mu_min      = params["mu_min"]
    mu_max      = params["mu_max"]
    max_mu_iter = params["max_mu_iter"]

    logger.debug(f"Loaded params: n_target={n_target}, T={T}, eps_n={eps_n}, "
                 f"mu_min={mu_min}, mu_max={mu_max}, max_mu_iter={max_mu_iter}")

    # Step A: Copy Delta.dat -> Delta.dat.prev if it exists
    if os.path.exists("Delta.dat"):
        try:
            shutil.copy("Delta.dat", "Delta.dat.prev")
        except Exception as e:
            raise DMFTError(f"Error copying Delta.dat->Delta.dat.prev: {e}")

    # Step B: check resigma.dat / imsigma.dat
    if not os.path.exists("resigma.dat"):
        raise DMFTError("'resigma.dat' not found.")
    if not os.path.exists("imsigma.dat"):
        raise DMFTError("'imsigma.dat' not found.")

    resigma_data = _read_two_column_data("resigma.dat")
    imsigma_data = _read_two_column_data("imsigma.dat")
    if len(resigma_data) != len(imsigma_data):
        raise DMFTError("resigma.dat and imsigma.dat differ in length.")

    # Combine
    sigma = []
    for (r_om, r_val), (i_om, i_val) in zip(resigma_data, imsigma_data):
        if abs(r_om - i_om) > 1e-12:
            raise DMFTError("Mismatch in omega for resigma/imsigma.")
        sigma.append((r_om, complex(r_val, i_val)))

    # Step C: define htDOS, compute G_loc
    def htDOS0(z):
        sgn = 1.0 if z.imag > 0 else -1.0
        tmp = cmath.sqrt(1.0 - z*z)
        correction = complex(0, -sgn)*tmp
        return 2.0*(z + correction)

    def htDOS(z):
        EPS = 1e-20
        re_z = z.real
        im_z = z.imag if z.imag > 0 else EPS
        return htDOS0(complex(re_z, im_z))

    G_loc = []
    for (om, sig) in sigma:
        zval = complex(om, 0) - sig
        G_val = htDOS(zval)
        G_loc.append((om, G_val))

    # write G_loc.dat
    try:
        with open("G_loc.dat", "w") as f:
            for (om, val) in G_loc:
                f.write(f"{om} {val.real} {val.imag}\n")
    except Exception as e:
        raise DMFTError(f"Error writing G_loc.dat: {e}")

    # A(omega)
    imaw_data = []
    reaw_data = []
    for (om, val) in G_loc:
        A_im = -1.0/math.pi * val.imag
        A_re = -1.0/math.pi * val.real
        imaw_data.append((om, A_im))
        reaw_data.append((om, A_re))

    _write_two_column_data("imaw.dat", imaw_data)
    _write_two_column_data("reaw.dat", reaw_data)

    # Step D: new Delta.dat => Im[1/G_loc + sigma]
    g0inv = []
    for (g_loc_tuple, sig_tuple) in zip(G_loc, sigma):
        om, G_loc_val = g_loc_tuple
        _, sig_val    = sig_tuple
        if abs(G_loc_val) < 1e-30:
            val = 0.0
        else:
            val = 1.0/G_loc_val + sig_val
        g0inv.append((om, val))

    Delta_data = []
    for (om, val) in g0inv:
        Delta_data.append((om, val.imag))

    _write_two_column_data("Delta.dat", Delta_data)

    # Step E: call kk if available
    if shutil.which("kk"):
        cmd = "kk Delta.dat Delta-re.dat"
        try:
            subprocess.check_call(cmd, shell=True)
        except subprocess.CalledProcessError as e:
            raise DMFTError(f"Command '{cmd}' failed: {e}")

    # Step F: Bisection for mu with real-time plotting
    imaw_data.sort(key=lambda x: x[0])
    mu_found, f_found, converged, iteration_data = find_mu_for_occupation(
        A_data=imaw_data,
        n_target=n_target,
        T=T,
        eps_n=eps_n,
        mu_min=mu_min,
        mu_max=mu_max,
        max_iter=max_mu_iter,
        iteration_label=str(iteration_index) if iteration_index is not None else None
    )

    final_occ = f_found + n_target
    logger.info(f"Bisection result:\n"
                f"   mu = {mu_found:.6f}\n"
                f"   occupation = {final_occ:.6f}\n"
                f"   F = {f_found:.6e}\n"
                f"   converged? {converged} (|F| < {eps_n})")

    logger.debug("execute_dmft() completed successfully.")