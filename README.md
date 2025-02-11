# DynaMeanX 
# DOI 10.5281/zenodo.14851936
This repository contains a set of Python modules and a `main.py` script to perform a DMFT (Dynamical Mean-Field Theory) calculation using NRG-based solvers and post-processing steps. It includes optional mixing methods to enhance convergence and a comprehensive logging system for monitoring and debugging.

## Table of Contents

- [Introduction](#introduction)
- [Features](#features)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [Mixing Methods](#mixing-methods)
  - [None](#none)
  - [Anderson Mixing](#anderson-mixing)
  - [Broyden Mixing](#broyden-mixing)
- [Logging](#logging)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)
- [License](#license)

## Introduction

The DMFT Project is a Python-based tool designed to automate and streamline the DMFT loop, facilitating the computation of hybridization functions and self-energy convergence. It leverages NRG-based solvers and incorporates optional mixing methods to improve convergence stability and speed. The application also features a robust logging system to aid in monitoring processes and debugging.

## Features

- **DMFT Iterations:** Automates the DMFT loop to compute and update hybridization functions (`Delta.dat`).
- **Mixing Methods:** Supports three mixing strategies to enhance convergence:
  - **None:** No mixing applied.
  - **Anderson Mixing:** Utilizes Anderson's method for mixing.
  - **Broyden Mixing:** Employs Broyden's method for mixing.
- **Logging:** Comprehensive logging system capturing all processes and mixing-specific logs.
- **Error Handling:** Robust error management ensuring graceful exits and informative logs.
- **Modular Design:** Organized into distinct modules for generation, simulation, averaging, and more.

### Module Breakdown

- **generate_delta.py:** Generates and updates the hybridization function `Delta.dat` and `Delta-re.dat`.
- **odesolv.py:** Executes ODE-based discretization for NRG.
- **simulation.py:** Runs impurity simulations with different `z`-values.
- **average.py:** Performs broadening/averaging of the output data.
- **realparts.py:** Calls the `kk` tool to compute real parts from imaginary parts.
- **sigmatrick.py:** Computes self-energy (`Sigma`) from imaginary and real Green’s functions.
- **dmft.py:** Finalizes the DMFT loop update of `Delta.dat`, calls `kk` if needed.
- **anderson.py:** Implements Anderson mixing method.
- **broyden.py:** Implements Broyden mixing method.

## Installation

### Prerequisites

1. **Python 3.8+**
   - **Linux/macOS:** Install via package manager or [Python.org](https://www.python.org/downloads/).
   - **Windows:** Download and install from [Python.org](https://www.python.org/downloads/).

2. **pip**
   - Comes bundled with Python 3. Ensure it's accessible via the command line.

3. **Conda** *(optional)*
   - If you prefer using Conda environments, install Miniconda or Anaconda from [here](https://docs.conda.io/en/latest/miniconda.html).

4. **NRG Ljubljana**
   - Provides external tools like `kk`, `nrg`, `nrginit`, `broaden`, and `adapt`.
   - **Installation Instructions:**
     - Visit: [NRG Ljubljana GitHub Repository](https://github.com/rokzitko/nrgljubljana)
     - Follow the provided instructions to install `kk`, `nrg`, `nrginit`, `broaden`, and `adapt`.

5. **Boost Library** *(macOS only)*
   - Required to address library path issues related to System Integrity Protection (SIP).
   - **Installation via Homebrew:**
     ```bash
     brew install boost
     ```
   - **Manual Installation:**
     - Download from [Boost Downloads](https://www.boost.org/users/download/).
     - Extract and install following the provided instructions.

6. **Mathematica**
   - A valid Mathematica license is required to use `nrg` and its utilities.

7. **Other External Dependencies**
   - Install any other external tools your project depends on (e.g., NRG solvers).
   - Ensure they are accessible via the system `PATH`.

### Steps

1. **Clone the Repository**
   ```bash
   git clone https://github.com/yourusername/my_dmft_project.git
   cd my_dmft_project
   ```

## License

This program is free software; you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation; either version 2 of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.

You should have received a copy of the GNU General Public License along with this program; if not, write to the Free Software Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA 02110-1301 USA

The full text of the GPL General Public License can be found in file LICENSE.
