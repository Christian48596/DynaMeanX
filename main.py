#!/usr/bin/env python3

import sys
import logging
import numpy as np
import shutil
import os
import matplotlib.pyplot as plt

def setup_logging():
    """
    Configures the logging settings for the entire application.
    """
    logger = logging.getLogger()  # Get the root logger
    logger.setLevel(logging.DEBUG)

    if not logger.handlers:
        # File handler for logging (captures DEBUG and above)
        fh = logging.FileHandler('application.log')
        fh.setLevel(logging.DEBUG)
        fh_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(name)s - %(message)s')
        fh.setFormatter(fh_formatter)
        logger.addHandler(fh)

        # Console handler for logging (captures INFO and above)
        ch = logging.StreamHandler()
        ch.setLevel(logging.INFO)
        ch_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        ch.setFormatter(ch_formatter)
        logger.addHandler(ch)

    return logger

# Set up logging
logger = setup_logging()

# Import application modules
from modules.ascii_banner import display_banner
from modules.parameter_parser import get_parameters
from modules.generate_delta import generate_Delta, GenerateDeltaError
from modules.odesolv import execute_ode_commands, ODESolverError
from modules.simulation import run_all_simulations, SimulationError
from modules.average import execute_average, AverageModuleError
from modules.realparts import execute_realparts, RealPartsError
from modules.sigmatrick import execute_sigmatrick, SigmaTrickError
# Note: now we import execute_dmft in a way that we can call execute_dmft(iteration_index=...)
from modules.dmft import execute_dmft, DMFTError

def check_convergence(old_data, new_data, eps_delta=1e-4):
    """
    Checks convergence by comparing two arrays.
    
    Returns a tuple (is_converged, max_difference), where:
      - is_converged is True if the maximum absolute difference is below eps_delta.
      - max_difference is the calculated maximum difference.
    """
    diff = np.max(np.abs(old_data - new_data))
    return (diff < eps_delta), diff

def main_dmft_loop(mixing_method, alpha):
    """
    Executes the main DMFT loop.

    1) If Delta.dat does not exist, an initial guess for Delta is generated.
    2) Convergence is determined by comparing Delta.dat and Delta.dat.prev,
       which is assumed to be updated automatically (e.g., by dmft.py).
    3) A plot is updated at each iteration to display the convergence behavior
       of the hybridization function.
    4) When convergence is achieved or the maximum iteration is reached,
       the plot is saved to convergence.pdf, then closed.
    
    Args:
        mixing_method (str): Mixing method parameter (parsed for compatibility, but not used).
        alpha (float): Mixing parameter (parsed for compatibility, but not used).
    """
    # Display ASCII banner
    display_banner()

    # Parse input parameters and convergence settings
    params = get_parameters()
    max_iter = int(params.get("max_iter", 10))
    eps_delta = float(params.get("eps_delta", 1e-4))

    converged = False

    # Initialize interactive plot for Delta.dat convergence
    plt.ion()
    fig, ax = plt.subplots()
    convergence_list = []
    iteration_list = []
    line, = ax.plot([], [], 'bo-', label=r'$\|\Delta - \Delta_{\mathrm{prev}}\|$')
    ax.axhline(y=eps_delta, color='r', linestyle='--', label=r'$\epsilon_{\Delta}$')

    ax.set_title(r'$\mathrm{Convergence\ Behavior:}\ \max|\Delta(\omega) - \Delta_{\mathrm{prev}}(\omega)|$')
    ax.set_xlabel(r'$\mathrm{Iteration}$')
    ax.set_ylabel(r'$\mathrm{Convergence\ Value}$')
    ax.legend()
    plt.show()

    for iteration in range(1, max_iter + 1):
        logger.info(f"=== DMFT Iteration {iteration} ===\n")

        # STEP 1: Generate initial guess for Delta if necessary
        if not os.path.exists("Delta.dat"):
            logger.info("Delta.dat not found. Generating initial guess...")
            try:
                delta_dat, delta_re_dat = generate_Delta(
                    params,
                    param_loop_path="param.loop",
                    gamma=0.3
                )
                logger.info("Generated Delta.dat and Delta-re.dat.")
            except GenerateDeltaError as e:
                logger.error(f"Error in generate_delta: {e}")
                sys.exit(1)
        else:
            logger.info("Delta.dat found. Skipping initial guess generation.")

        # STEP 2: Execute ODE solver
        logger.info("Executing ODE solver commands...")
        try:
            execute_ode_commands()
            logger.info("ODE solver completed.")
        except ODESolverError as e:
            logger.error(f"ODE solver error: {e}")
            sys.exit(1)

        # STEP 3: Run simulations
        logger.info("Running simulations...")
        try:
            run_all_simulations(params, verbose=False)
            logger.info("Simulations completed.")
        except SimulationError as e:
            logger.error(f"Simulation error: {e}")
            sys.exit(1)

        # STEP 4: Averaging (broadening)
        logger.info("Executing averaging...")
        try:
            execute_average()
            logger.info("Averaging completed.")
        except AverageModuleError as e:
            logger.error(f"Averaging error: {e}")
            sys.exit(1)

        # STEP 5: Compute real parts
        logger.info("Computing real parts from imaginary data...")
        try:
            execute_realparts()
            logger.info("Real parts computed.")
        except RealPartsError as e:
            logger.error(f"Realparts error: {e}")
            sys.exit(1)

        # STEP 6: Final self-energy (sigmatrick)
        logger.info("Computing self-energy with sigmatrick...")
        try:
            execute_sigmatrick()
            logger.info("Sigmatrick step completed.")
        except SigmaTrickError as e:
            logger.error(f"Sigmatrick error: {e}")
            sys.exit(1)

        # STEP 7: DMFT step
        logger.info(f"Running DMFT step (iteration {iteration})...")
        try:
            # Pass iteration index => produce a unique bisection_convergence PDF each time
            execute_dmft(iteration_index=iteration)
            logger.info("DMFT step completed.")
        except DMFTError as e:
            logger.error(f"DMFT error: {e}")
            sys.exit(1)

        # STEP 8: Convergence check: Delta.dat vs. Delta.dat.prev
        conv_val = None
        if os.path.exists("Delta.dat.prev"):
            try:
                delta_current = np.loadtxt("Delta.dat")[:, 1]
                delta_prev    = np.loadtxt("Delta.dat.prev")[:, 1]
            except Exception as e:
                logger.error(f"Error reading Delta files: {e}")
                sys.exit(1)

            is_converged, conv_val = check_convergence(delta_prev, delta_current, eps_delta)
            logger.info(f"Iteration {iteration}: Delta difference = {conv_val:.3e} "
                        f"(eps_delta = {eps_delta:.3e}, Ratio = {conv_val/eps_delta:.3f})")

            if is_converged:
                logger.info(f"Hybridization function Delta converged at iteration {iteration}!")
                converged = True
        else:
            logger.debug("Delta.dat.prev not found; skipping convergence check this iteration.")
            conv_val = float('nan')

        # Update the hybridization convergence plot
        iteration_list.append(iteration)
        convergence_list.append(conv_val)
        line.set_data(iteration_list, convergence_list)

        ax.relim()
        ax.autoscale_view()
        plt.draw()
        plt.pause(0.1)

        if converged:
            break

    # After the DMFT loop
    logger.info("Saving convergence graph to 'convergence.pdf' and closing.")
    plt.savefig("convergence.pdf")
    plt.close(fig)

def main():
    # Parse parameters
    params = get_parameters()

    # Extract optional mixing
    mixing_method = params.get("mixing_method", "none").lower()
    try:
        alpha = float(params.get("mixing_parameter", 0.1))
        if not (0 < alpha <= 1):
            logger.error(f"Invalid mixing_parameter (alpha): {alpha}. Must be between 0 and 1.")
            sys.exit(1)
    except ValueError:
        logger.error("Invalid mixing_parameter; must be a float in (0,1].")
        sys.exit(1)

    logger.debug(f"Mixing parameter (alpha): {alpha}")

    # Launch main DMFT loop
    try:
        main_dmft_loop(mixing_method, alpha)
    except Exception as e:
        logger.critical(f"Critical error in main: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()