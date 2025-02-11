# modules/parameter_parser.py

import os
import re
import logging

# Initialize a logger for the parameter_parser module
logger = logging.getLogger('parameter_parser')

class SimulationError(Exception):
    """Custom exception for simulation errors."""
    pass

def parse_param_loop(filename):
    """
    Parses the param.loop file and extracts relevant parameters for DMFT and Delta generation.
    Lines starting with '@' or '$' are considered as control commands and are skipped.
    
    Args:
        filename (str): Path to the param.loop file.
    
    Returns:
        dict: Dictionary containing parameter names and their values (as strings).
    
    Raises:
        RuntimeError: If there's an issue reading or parsing the file.
    """
    params = {}
    current_section = None

    # Extend the recognized keys in the [param] section to include eps_n, mu_min, mu_max, max_mu_iter, etc.
    section_params = {
        "extra": ["U", "epsilon"],
        "param": [
            "symtype", "Lambda", "Tmin", "keepmin", "keepenergy", "keep",
            "band", "dos", "bandrescale", "discretization", "ops", "specd", "fdm",
            "broaden_max", "broaden_ratio", "broaden_min", "broaden_alpha", "broaden_gamma",
            "bins", "broaden", "savebins", "T", "model", "Nz", "mixing_method",
            "mixing_parameter", "n_target", "N_matsubara",
            "eps_n", "mu_min", "mu_max", "max_mu_iter"
        ]
    }

    try:
        with open(filename, 'r') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                # Skip lines starting with '@' or '$'
                if line.startswith('@') or line.startswith('$'):
                    continue

                # Check for section headers, e.g., [section]
                section_match = re.match(r'\[(.+)\]', line)
                if section_match:
                    current_section = section_match.group(1).strip().lower()
                    continue

                # Parse key=value pairs
                if '=' in line:
                    key, value = line.split('=', 1)
                    key = key.strip()
                    value = value.strip()

                    # Skip variable assignments that start with '$' or '@'
                    if key.startswith('$') or key.startswith('@'):
                        continue

                    # If we are in a recognized section, store the parameter
                    if (current_section
                        and key in section_params.get(current_section, [])):
                        params[key] = value
                    # If not in a recognized section but the key is in [param] by default
                    elif (not current_section
                          and key in section_params.get("param", [])):
                        params[key] = value

    except FileNotFoundError:
        logger.error(f"Parameter file '{filename}' not found.")
        raise RuntimeError(f"Parameter file '{filename}' not found.")
    except Exception as e:
        logger.error(f"Error parsing '{filename}': {e}")
        raise RuntimeError(f"Error parsing '{filename}': {e}")

    return params

def get_parameters(param_loop_path="param.loop"):
    """
    Retrieves parameters from param.loop if present, else uses default values.
    Command-line arguments have been removed to maintain compatibility with other scripts.
    
    Returns:
        dict: Dictionary containing all necessary parameters with appropriate types and defaults.
    
    Raises:
        RuntimeError: If required parameters are missing or have invalid formats.
    """
    # --------------------------
    # 1) Default parameter sets
    # --------------------------

    # DMFT-specific defaults
    default_dmft_params = {
        "U":        4.0,   # Coulomb repulsion
        "ed":       0.0,   # On-site energy (or epsilon)
        "V":        1.0,   # Hybridization strength
        "beta":     50.0,  # If you used to treat T as 1/beta, keep this for old code
        "alpha":    0.5,   # 'alpha' is mapped to 'mixing_parameter' in main.py
        "max_iter": 30,
        "eps_delta":1e-4,
        "omega_min":-4.0,
        "omega_max": 4.0,
        "n_omega":  300
    }

    # Delta generation defaults
    default_delta_params = {
        "broaden_max":   10.0,
        "broaden_ratio": 1.05,
        "broaden_min":   0.01,
        "broaden_alpha": 0.4,
        "broaden_gamma": 0.2,
        "bins":          300,
        "broaden":       False,
        "savebins":      True
    }

    # Additional defaults for newly added parameters
    # We'll treat T as a direct temperature, distinct from 'beta':
    default_new_params = {
        "T":          0.02,    # Temperature (if you want it distinct from 1/beta)
        "eps_n":      1e-4,    # Occupation tolerance
        "mu_min":     -10.0,   # Lower bound for mu search
        "mu_max":     10.0,    # Upper bound for mu search
        "max_mu_iter":100      # Iterations for the bisection
    }

    # Combine all defaults
    default_params = {**default_dmft_params, **default_delta_params, **default_new_params}

    # --------------------------
    # 2) Parse param.loop if present
    # --------------------------
    if os.path.isfile(param_loop_path):
        try:
            file_params = parse_param_loop(param_loop_path)
            # Merge parsed parameters with defaults (parsed parameters take precedence)
            params = {**default_params, **file_params}
            logger.debug(f"Parameters parsed from '{param_loop_path}': {file_params}")
        except RuntimeError as e:
            logger.error(f"Error parsing 'param.loop': {e}")
            logger.info("Using default parameters.")
            params = default_params.copy()
    else:
        logger.info(f"Parameter file '{param_loop_path}' not found. Using default parameters.")
        params = default_params.copy()

    # --------------------------
    # 3) Convert to proper types
    # --------------------------
    mapped_params = {}
    try:
        # DMFT Parameters
        mapped_params["U"] = float(params.get("U", default_dmft_params["U"]))
        mapped_params["ed"] = float(params.get("epsilon", default_dmft_params["ed"]))
        mapped_params["V"] = float(params.get("V", default_dmft_params["V"]))

        # If your code used 'T' as 1/beta, do the conversion:
        # But here we interpret 'T' as the actual temperature:
        mapped_params["T"] = float(params.get("T", default_new_params["T"]))

        # For backward compatibility, we keep 'beta' if used
        mapped_params["beta"] = float(params.get("beta", default_dmft_params["beta"]))

        # DMFT Loop / mesh
        mapped_params["max_iter"]   = int(params.get("max_iter",   default_dmft_params["max_iter"]))
        mapped_params["eps_delta"]  = float(params.get("eps_delta",default_dmft_params["eps_delta"]))
        mapped_params["omega_min"]  = float(params.get("omega_min",default_dmft_params["omega_min"]))
        mapped_params["omega_max"]  = float(params.get("omega_max",default_dmft_params["omega_max"]))
        mapped_params["n_omega"]    = int(params.get("n_omega",    default_dmft_params["n_omega"]))

        # Delta Generation
        mapped_params["broaden_max"]   = float(params.get("broaden_max",   default_delta_params["broaden_max"]))
        mapped_params["broaden_ratio"] = float(params.get("broaden_ratio", default_delta_params["broaden_ratio"]))
        mapped_params["broaden_min"]   = float(params.get("broaden_min",   default_delta_params["broaden_min"]))
        mapped_params["broaden_alpha"] = float(params.get("broaden_alpha", default_delta_params["broaden_alpha"]))
        mapped_params["broaden_gamma"] = float(params.get("broaden_gamma", default_delta_params["broaden_gamma"]))
        mapped_params["bins"]          = int(params.get("bins",            default_delta_params["bins"]))
        mapped_params["broaden"]       = params.get("broaden",    "false").lower() == "true"
        mapped_params["savebins"]      = params.get("savebins",   "true").lower()  == "true"

        # Additional legacy / general params
        mapped_params["symtype"]       = params.get("symtype", "QS")
        mapped_params["Lambda"]        = float(params.get("Lambda", 3.0))
        mapped_params["Tmin"]          = float(params.get("Tmin", 1e-8))
        mapped_params["keepmin"]       = int(params.get("keepmin", 200))
        mapped_params["keepenergy"]    = float(params.get("keepenergy", 8.0))
        mapped_params["keep"]          = int(params.get("keep", 10000))
        mapped_params["band"]          = params.get("band", "asymode")
        mapped_params["discretization"]= params.get("discretization", "Z")
        mapped_params["ops"]           = params.get("ops", "A_d self_d n_d")
        mapped_params["specd"]         = params.get("specd", "A_d-A_d self_d-A_d")
        mapped_params["fdm"]           = params.get("fdm", "false").lower() == "true"
        mapped_params["model"]         = params.get("model", "model.m")
        mapped_params["overwrite"]     = params.get("overwrite", "true").lower() == "true"

        # Nz Parameter
        mapped_params["Nz"] = int(params.get("Nz", default_dmft_params["n_omega"]))

        # Mixing
        mapped_params["mixing_method"]    = params.get("mixing_method", "none").lower()
        mapped_params["mixing_parameter"] = float(params.get("mixing_parameter", 0.1))

        # mu
        mapped_params["n_target"]     = float(params.get("n_target", 0.8))
        mapped_params["eps_n"]       = float(params.get("eps_n",      default_new_params["eps_n"]))
        mapped_params["mu_min"]      = float(params.get("mu_min",     default_new_params["mu_min"]))
        mapped_params["mu_max"]      = float(params.get("mu_max",     default_new_params["mu_max"]))
        mapped_params["max_mu_iter"] = int(params.get("max_mu_iter", default_new_params["max_mu_iter"]))

    except ValueError as ve:
        logger.error(f"Invalid parameter format: {ve}")
        raise RuntimeError(f"Invalid parameter format: {ve}")
    except Exception as e:
        logger.error(f"Error mapping parameters: {e}")
        raise RuntimeError(f"Error mapping parameters: {e}")

    return mapped_params