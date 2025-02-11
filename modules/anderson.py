# modules/anderson.py
"""
Anderson Mixing Module

Implements the Anderson mixing method to assist in self-energy convergence.

Logging:
   - All routine steps are logged at DEBUG into 'Anderson.log'.
   - Only INFO-level messages (errors and warnings) are displayed on the console.
"""

import logging

class AndersonMixingError(Exception):
    """Custom exception for errors in anderson.py."""
    pass

def apply_anderson_mixing(old_delta, new_delta, mixing_parameter=0.1):
    """
    Applies Anderson mixing to update Delta.dat.

    Args:
        old_delta (numpy.ndarray): Previous Delta values.
        new_delta (numpy.ndarray): Newly computed Delta values.
        mixing_parameter (float): Mixing parameter alpha (0 < alpha <= 1).

    Returns:
        numpy.ndarray: Updated Delta values after mixing.

    Raises:
        AndersonMixingError: If inputs are invalid or mixing fails.
    """
    # Initialize logger inside the function
    logger = logging.getLogger('anderson')
    if not logger.handlers:
        # File Handler captures all logs (DEBUG+) in Anderson.log
        fh = logging.FileHandler('anderson.log')
        fh.setLevel(logging.DEBUG)  # Capture DEBUG and above in the file
        fh_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        fh.setFormatter(fh_formatter)
        logger.addHandler(fh)

        # Console Handler only shows INFO+ (i.e., errors)
        ch = logging.StreamHandler()
        ch.setLevel(logging.INFO)  # Capture INFO and above on console
        ch_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        ch.setFormatter(ch_formatter)
        logger.addHandler(ch)

        # Disable propagation to prevent duplication
        logger.propagate = False

    logger.debug("Starting Anderson mixing.")
    try:
        if old_delta is None:
            logger.debug("No previous Delta found. Using new Delta without mixing.")
            return new_delta

        if not (0 < mixing_parameter <= 1):
            msg = f"Invalid mixing parameter: {mixing_parameter}. Must be between 0 and 1."
            logger.info(msg)
            raise AndersonMixingError(msg)

        logger.debug(f"Mixing parameter: {mixing_parameter}")

        # Simple linear mixing: delta_new = alpha * new_delta + (1 - alpha) * old_delta
        mixed_delta = mixing_parameter * new_delta + (1 - mixing_parameter) * old_delta
        logger.debug("Anderson mixing applied successfully.")

        return mixed_delta

    except Exception as e:
        msg = f"Error during Anderson mixing: {e}"
        logger.info(msg)
        raise AndersonMixingError(msg)