# modules/odesolv.py

import subprocess
import sys
import os
import logging
from datetime import datetime
from logging.handlers import RotatingFileHandler

class ODESolverError(Exception):
    """Custom exception for ODE Solver errors."""
    pass

def setup_logging():
    """
    Configures the logging settings for odesolv.py.

    Returns:
        logging.Logger: Configured logger instance.
    """
    logger = logging.getLogger('ODESolver')
    logger.setLevel(logging.DEBUG)  # Set to DEBUG to capture all messages

    # Prevent adding multiple handlers if this function is called multiple times
    if not logger.handlers:
        # Rotating File Handler: Keeps the log file size manageable
        fh = RotatingFileHandler('odesolv.log', maxBytes=5*1024*1024, backupCount=5)
        fh.setLevel(logging.DEBUG)  # Record DEBUG+ in the file
        fh_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        fh.setFormatter(fh_formatter)
        logger.addHandler(fh)

        # Console Handler: We only show INFO-level logs (i.e., errors in our new scheme)
        ch = logging.StreamHandler()
        ch.setLevel(logging.INFO)  # Show INFO+ on console
        ch_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        ch.setFormatter(ch_formatter)
        logger.addHandler(ch)

        # Prevent log messages from propagating to the root logger
        logger.propagate = False

    return logger

def run_and_log(command, logfile, logger):
    """
    Executes a shell command and writes its output to a logfile and console.

    Args:
        command (str): The command to execute (e.g., "adapt P param.loop").
        logfile (str): The path to the log file where output will be written.
        logger (logging.Logger): The logger instance for logging messages.

    Raises:
        ODESolverError: If the command fails to execute properly.
    """
    try:
        # Log routine steps at DEBUG level
        logger.debug(f"--- Command '{command}' started at {datetime.now()} ---")

        # Prepare environment variables
        env = os.environ.copy()
        boost_lib_path = "/Users/christian.tantardini/Softs/boost_1_84_0/lib"
        existing_dyld = env.get("DYLD_LIBRARY_PATH", "")
        env["DYLD_LIBRARY_PATH"] = f"{boost_lib_path}:{existing_dyld}"
        logger.debug(f"DYLD_LIBRARY_PATH set to: {env['DYLD_LIBRARY_PATH']}")

        # Execute the command
        process = subprocess.Popen(
            command,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            env=env
        )

        # Stream the output to both the logfile and console
        with open(logfile, 'a') as f:
            for line in process.stdout:
                f.write(line)
                # Also log routine output at DEBUG
                logger.debug(line.strip())

        # Wait for the command to complete
        process.wait()

        # Check for errors
        if process.returncode != 0:
            error_message = f"Command '{command}' exited with return code {process.returncode}"
            # Log errors at INFO so user will see them
            logger.info(error_message)
            raise ODESolverError(error_message)
        else:
            logger.debug(f"Command '{command}' completed successfully at {datetime.now()}.")

    except subprocess.CalledProcessError as e:
        error_msg = f"Command '{command}' failed: {e}"
        logger.info(error_msg)
        raise ODESolverError(error_msg)
    except Exception as e:
        error_msg = f"An unexpected error occurred while running command '{command}': {e}"
        logger.info(error_msg)
        raise ODESolverError(error_msg)

def execute_ode_commands():
    """
    Executes predefined ODE solver commands and logs their outputs.

    Raises:
        ODESolverError: If any command fails to execute properly.
    """
    logger = setup_logging()

    param_filename = "param.loop"
    if not os.path.isfile(param_filename):
        error_msg = f"Parameter file '{param_filename}' does not exist."
        logger.info(error_msg)
        raise ODESolverError(error_msg)

    commands = [
        (f"adapt P {param_filename}", "solverlog"),
        (f"adapt N {param_filename}", "solverlogneg")
    ]

    for cmd, log in commands:
        run_and_log(cmd, log, logger)