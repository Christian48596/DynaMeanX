#!/usr/bin/env bash

#
# install.sh
# ----------
# Installation script for the DMFT Project.
# Handles environment setup, dependency checks, and executable creation.
#
# Usage: ./install.sh
#

# Exit immediately if a command exits with a non-zero status
set -e

# Function to print error messages in red
function echo_error {
    echo -e "\\033[0;31m$1\\033[0m"  # Red color
}

# Function to print success messages in green
function echo_success {
    echo -e "\\033[0;32m$1\\033[0m"  # Green color
}

# Function to print info messages in blue
function echo_info {
    echo -e "\\033[1;34m$1\\033[0m"  # Blue color
}

# Function to display help message
function show_help {
    echo "Usage: ./install.sh"
    echo "This script installs and configures the DMFT Project."
    echo "Ensure you have the necessary permissions and prerequisites before running."
}

# If user passes -h or --help, show help
if [[ "$1" == "-h" || "$1" == "--help" ]]; then
    show_help
    exit 0
fi

echo_info "=============================="
echo_info "   DMFT Project Installation  "
echo_info "==============================\n"

# 1. Detect Operating System
OS_TYPE=$(uname)
echo_info "Detected Operating System: $OS_TYPE"

# 2. Detect if in a Conda environment
if [[ -n "$CONDA_PREFIX" ]]; then
    ENV_TYPE="conda"
    echo_success "Conda environment detected: $(basename "$CONDA_PREFIX")"
else
    # 3. Detect if in a virtualenv
    if [[ -n "$VIRTUAL_ENV" ]]; then
        ENV_TYPE="virtualenv"
        echo_success "Virtual environment detected: $(basename "$VIRTUAL_ENV")"
    else
        ENV_TYPE="system"
        echo_info "No Conda or virtual environment detected."
        # Prompt to create a virtual environment
        while true; do
            echo_info "Would you like to create and activate a Python virtual environment? [y/n]"
            read -r -p "Enter your choice: " CREATE_VENV_CHOICE
            case "$CREATE_VENV_CHOICE" in
                [Yy]* )
                    echo_info "Creating virtual environment 'venv'..."
                    python3 -m venv venv
                    echo_success "Virtual environment 'venv' created."
                    echo_info "Activating virtual environment..."
                    source venv/bin/activate
                    echo_success "Virtual environment activated."
                    ENV_TYPE="virtualenv"
                    break
                    ;;
                [Nn]* )
                    echo_info "Proceeding without a virtual environment."
                    break
                    ;;
                * )
                    echo_error "Invalid choice. Please respond with 'y' or 'n'."
                    ;;
            esac
        done
    fi
fi

# 4. Check for Python installation
if command -v python3 &>/dev/null; then
    PYTHON_CMD=python3
elif command -v python &>/dev/null; then
    PYTHON_CMD=python
else
    echo_error "Python is not installed. Attempting to install Python 3.8+..."

    if [[ "$OS_TYPE" == "Darwin" ]]; then
        # macOS
        if ! command -v brew &>/dev/null; then
            echo_info "Homebrew not found. Installing Homebrew..."
            /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
            echo_success "Homebrew installed successfully."
            # Add Homebrew to PATH
            echo 'eval "$(/opt/homebrew/bin/brew shellenv)"' >> ~/.zprofile
            eval "$(/opt/homebrew/bin/brew shellenv)"
        fi

        echo_info "Installing Python via Homebrew..."
        brew install python@3.9  # Install Python 3.9; adjust as needed
        echo_success "Python installed successfully via Homebrew."
        PYTHON_CMD=python3
    elif [[ "$OS_TYPE" == "Linux" ]]; then
        # Detect Linux distribution
        if [[ -f /etc/os-release ]]; then
            . /etc/os-release
            DISTRO=$ID
        else
            DISTRO=$(uname -s)
        fi

        case "$DISTRO" in
            ubuntu|debian)
                echo_info "Detected Debian-based Linux ($DISTRO). Installing Python 3.8+ using apt..."
                sudo apt-get update
                sudo apt-get install -y python3.8 python3.8-venv python3.8-dev
                # Optionally, set python3 to point to python3.8
                sudo update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.8 1
                echo_success "Python 3.8 installed successfully via apt."
                PYTHON_CMD=python3
                ;;
            fedora)
                echo_info "Detected Fedora. Installing Python 3.8+ using dnf..."
                sudo dnf install -y python38 python38-venv python38-devel
                sudo alternatives --install /usr/bin/python3 python3 /usr/bin/python3.8 1
                echo_success "Python 3.8 installed successfully via dnf."
                PYTHON_CMD=python3
                ;;
            arch)
                echo_info "Detected Arch Linux. Installing Python 3.9 using pacman..."
                sudo pacman -Syu --noconfirm python
                echo_success "Python installed successfully via pacman."
                PYTHON_CMD=python
                ;;
            *)
                echo_error "Unsupported Linux distribution: $DISTRO. Please install Python 3.8+ manually and rerun this script."
                exit 1
                ;;
        esac
    else
        echo_error "Unsupported Operating System: $OS_TYPE. Please install Python 3.8+ manually and rerun this script."
        exit 1
    fi

    # Verify Python installation
    if ! command -v "$PYTHON_CMD" &>/dev/null; then
        echo_error "Python installation failed. Please install Python 3.8+ manually and rerun this script."
        exit 1
    fi
fi

# 5. Check Python version (minimum 3.8)
PYTHON_VERSION=$($PYTHON_CMD -c 'import sys; print(".".join(map(str, sys.version_info[:3])))')
REQUIRED_PYTHON_VERSION="3.8.0"

# Compare versions
if [[ "$(printf '%s\n' "$REQUIRED_PYTHON_VERSION" "$PYTHON_VERSION" | sort -V | head -n1)" != "$REQUIRED_PYTHON_VERSION" ]]; then 
    echo_error "Python version is $PYTHON_VERSION. Python 3.8+ is required."
    exit 1
fi

echo_success "Python $PYTHON_VERSION detected."

# 6. Check for pip installation
if ! command -v pip &>/dev/null; then
    echo_error "pip is not installed. Attempting to install pip..."

    # Use get-pip.py to install pip
    curl https://bootstrap.pypa.io/get-pip.py -o get-pip.py
    $PYTHON_CMD get-pip.py
    rm get-pip.py

    echo_success "pip installed successfully."
else
    echo_success "pip is installed."
fi

# 7. Install required Python packages
# List of required packages (excluding standard libraries)
REQUIRED_PACKAGES=("numpy" "scipy" "matplotlib")  # Add other required packages here

# Function to check if a Python package is installed
function is_package_installed {
    PACKAGE=$1
    if [[ "$ENV_TYPE" == "conda" ]]; then
        conda list "$PACKAGE" &>/dev/null
    else
        pip show "$PACKAGE" &>/dev/null
    fi
}

# Identify missing packages
MISSING_PACKAGES=()
for PACKAGE in "${REQUIRED_PACKAGES[@]}"; do
    if ! is_package_installed "$PACKAGE"; then
        MISSING_PACKAGES+=("$PACKAGE")
    fi
done

# Install missing packages
if [ ${#MISSING_PACKAGES[@]} -ne 0 ]; then
    echo_info "Installing missing Python packages: ${MISSING_PACKAGES[*]}..."

    if [[ "$ENV_TYPE" == "conda" ]]; then
        # Try to install via conda first
        for PACKAGE in "${MISSING_PACKAGES[@]}"; do
            conda install -y "$PACKAGE" || pip install "$PACKAGE"
        done
    else
        # Install using pip
        pip install "${MISSING_PACKAGES[@]}"
    fi

    echo_success "Installed the following Python packages: ${MISSING_PACKAGES[*]}."
else
    echo_success "All required Python packages are already installed: ${REQUIRED_PACKAGES[*]}."
fi

# 8. Check for external dependencies (e.g., 'kk', 'nrg', 'nrginit', 'broaden', 'adapt')
echo_info "Checking for external dependencies..."

# Function to check if a command exists
function check_command {
    CMD=$1
    if ! command -v "$CMD" &>/dev/null; then
        echo_error "External dependency '$CMD' is not installed or not in PATH."
        MISSING_EXTERNAL=1
    else
        echo_success "External dependency '$CMD' is available."
    fi
}

MISSING_EXTERNAL=0

# Updated list of external commands your project depends on
EXTERNAL_COMMANDS=("kk" "nrg" "nrginit" "broaden" "adapt")  # Add other external executables if needed

for CMD in "${EXTERNAL_COMMANDS[@]}"; do
    check_command "$CMD"
done

# 9. Handle missing external dependencies
if [ "$MISSING_EXTERNAL" -eq 1 ]; then
    echo_error "One or more external dependencies are missing."
    echo_info "Please install 'NRG Ljubljana' with 'mpirun' as it provides the required tools."
    echo_info "Visit: https://github.com/rokzitko/nrgljubljana"
    exit 1
fi

# 10. Check for mpirun
echo_info "Checking for 'mpirun'..."

if ! command -v mpirun &>/dev/null; then
    echo_error "'mpirun' is not installed or not in PATH."
    echo_info "To execute 'nrg' and its utilities, 'mpirun' is required."
    echo_info "Please install an MPI implementation (e.g., OpenMPI or MPICH) and ensure 'mpirun' is accessible in your PATH."
    echo_info "After installing MPI, ensure 'nrg' is properly configured with MPI."
    exit 1
else
    echo_success "'mpirun' is available."
    
    # Prompt the user about nrg configuration
    while true; do
        echo_info "Has 'nrg' been installed with the necessary configuration to use it? [y/n]"
        read -r -p "Enter your choice: " NRG_CONFIG_CHOICE
        case "$NRG_CONFIG_CHOICE" in
            [Yy]* )
                echo_success "'nrg' is properly configured."
                break
                ;;
            [Nn]* )
                echo_error "'nrg' is not properly configured."
                echo_info "Please install and configure 'nrg' with MPI support."
                echo_info "Refer to the NRG Ljubljana documentation: https://github.com/rokzitko/nrgljubljana"
                exit 1
                ;;
            * )
                echo_error "Invalid choice. Please respond with 'y' or 'n'."
                ;;
        esac
    done
fi

# 11. Additional Steps for macOS: Handling SIP and Boost Library Path
if [[ "$OS_TYPE" == "Darwin" ]]; then
    echo_info "Detected macOS. Checking for Boost library path issues related to System Integrity Protection (SIP)..."

    # Define paths to search for libboost_serialization.dylib
    BOOST_LIB_PATHS=(
        "/usr/local/lib"
        "/opt/homebrew/lib"
    )

    echo_info "Searching for 'libboost_serialization.dylib' in common directories..."

    # Search for the Boost library
    FOUND_BOOST_LIB=$(find "${BOOST_LIB_PATHS[@]}" -name "libboost_serialization.dylib" 2>/dev/null | head -n 1)

    if [[ -n "$FOUND_BOOST_LIB" ]]; then
        echo_success "Found 'libboost_serialization.dylib' at: $FOUND_BOOST_LIB"

        # Extract the directory path from the Boost library
        BOOST_LIB_DIR=$(dirname "$FOUND_BOOST_LIB")

        # Prompt the user whether to update rpath for external executables
        while true; do
            echo_info "Would you like to update the rpath for external executables ('kk', 'adapt', 'broaden') to include the Boost library path? [y/n]"
            read -r -p "Enter your choice: " UPDATE_RPATH_CHOICE
            case "$UPDATE_RPATH_CHOICE" in
                [Yy]* )
                    echo_success "Updating rpath for external executables..."
                    EXECUTABLES=("kk" "adapt" "broaden")

                    for EXEC in "${EXECUTABLES[@]}"; do
                        EXEC_PATH=$(which "$EXEC")
                        if [[ -f "$EXEC_PATH" ]]; then
                            echo_info "Updating rpath for '$EXEC' executable to include Boost library path..."

                            # Update the rpath using install_name_tool
                            sudo install_name_tool -add_rpath "$BOOST_LIB_DIR" "$EXEC_PATH"

                            echo_success "rpath updated successfully for '$EXEC'."
                        else
                            echo_error "Executable '$EXEC' not found at expected path: $EXEC_PATH"
                            echo_info "Please ensure '$EXEC' is installed correctly."
                        fi
                    done
                    break
                    ;;
                [Nn]* )
                    echo_info "You chose not to update the rpath for external executables."
                    echo_info "Proceeding without updating rpath."
                    break
                    ;;
                * )
                    echo_error "Invalid choice. Please respond with 'y' or 'n'."
                    ;;
            esac
        done
    else
        echo_error "'libboost_serialization.dylib' not found in the specified directories."

        # Interactive prompt for the user to specify Boost library path
        while true; do
            echo_info "Would you like to specify the path to 'libboost_serialization.dylib'? [y/n]"
            read -r -p "Enter your choice: " CHOICE
            case "$CHOICE" in
                [Yy]* )
                    read -r -p "Please enter the absolute path to 'libboost_serialization.dylib': " USER_BOOST_PATH
                    if [[ -f "$USER_BOOST_PATH" ]]; then
                        BOOST_LIB_DIR=$(dirname "$USER_BOOST_PATH")
                        echo_success "Found 'libboost_serialization.dylib' at: $USER_BOOST_PATH"

                        # Prompt the user whether to update rpath for external executables
                        while true; do
                            echo_info "Would you like to update the rpath for external executables ('kk', 'adapt', 'broaden') to include the Boost library path? [y/n]"
                            read -r -p "Enter your choice: " UPDATE_RPATH_CHOICE
                            case "$UPDATE_RPATH_CHOICE" in
                                [Yy]* )
                                    echo_success "Updating rpath for external executables..."
                                    EXECUTABLES=("kk" "adapt" "broaden")

                                    for EXEC in "${EXECUTABLES[@]}"; do
                                        EXEC_PATH=$(which "$EXEC")
                                        if [[ -f "$EXEC_PATH" ]]; then
                                            echo_info "Updating rpath for '$EXEC' executable to include Boost library path..."

                                            # Update the rpath using install_name_tool
                                            sudo install_name_tool -add_rpath "$BOOST_LIB_DIR" "$EXEC_PATH"

                                            echo_success "rpath updated successfully for '$EXEC'."
                                        else
                                            echo_error "Executable '$EXEC' not found at expected path: $EXEC_PATH"
                                            echo_info "Please ensure '$EXEC' is installed correctly."
                                        fi
                                    done
                                    break
                                    ;;
                                [Nn]* )
                                    echo_info "You chose not to update the rpath for external executables."
                                    echo_info "Proceeding without updating rpath."
                                    break
                                    ;;
                                * )
                                    echo_error "Invalid choice. Please respond with 'y' or 'n'."
                                    ;;
                            esac
                        done
                        break
                    else
                        echo_error "The file '$USER_BOOST_PATH' does not exist."
                        echo_info "Please ensure you entered the correct path."
                    fi
                    ;;
                [Nn]* )
                    echo_info "Would you like to proceed without updating rpath? (Assuming SIP is disabled)"
                    read -r -p "Enter your choice [y/n]: " PROCEED_CHOICE
                    case "$PROCEED_CHOICE" in
                        [Yy]* )
                            echo_info "Proceeding without updating rpath."
                            break
                            ;;
                        [Nn]* )
                            echo_info "Exiting installation as rpath update is necessary."
                            exit 1
                            ;;
                        * )
                            echo_error "Invalid choice. Please respond with 'y' or 'n'."
                            ;;
                    esac
                    ;;
                * )
                    echo_error "Invalid choice. Please respond with 'y' or 'n'."
                    ;;
            esac
        done
    fi
fi

# 12. Check for PyInstaller and Install if Necessary
echo_info "Checking for PyInstaller..."

if ! command -v pyinstaller &>/dev/null; then
    echo_info "PyInstaller not found. Installing PyInstaller using pip..."
    pip install pyinstaller
    echo_success "PyInstaller installed successfully."
else
    echo_success "PyInstaller is already installed."
fi

# 13. Create the Executable using PyInstaller
echo_info "Creating the executable 'dmft_ipb' using PyInstaller..."

# Navigate to the project directory
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"

# Define data files to include (only static input files, if any)
# Since 'Delta.dat' and 'Delta-re.dat' are generated by the script, we exclude them.
# 'model.m' is an input file provided by the user and should remain in the working directory.
# Therefore, we do NOT include 'model.m' as a data file to allow flexibility.

# Uncomment and modify the following lines if you have other static data files to include.
# DATA_FILES=(
#     "another_static_file.dat"
#     # Add other static data files or directories as needed
# )

# Check if data files exist before bundling (if any)
# for DATA in "${DATA_FILES[@]}"; do
#     if [[ ! -f "$DATA" ]]; then
#         echo_error "Data file '$DATA' not found in the project directory."
#         echo_info "Please ensure '$DATA' is present before building the executable."
#         exit 1
#     fi
# done

# Construct the --add-data argument for PyInstaller (if any)
# ADD_DATA=""
# for DATA in "${DATA_FILES[@]}"; do
#     ADD_DATA+="--add-data \"$DATA:./\" "
# done

# Run PyInstaller without adding data files since 'model.m' and output files are handled externally
pyinstaller --onefile --name dmft_ipb main.py

echo_success "Executable 'dmft_ipb' created successfully in the 'dist' directory."

# Optional: Move the executable to the project directory root (if PyInstaller creates a separate folder)
# mv dist/dmft_ipb "$PROJECT_DIR/"

# 14. Final Messages
echo_success "\nInstallation and setup completed successfully!"

# Advise the user to add the dist directory to their PATH (optional)
echo_info "To run the project executable 'dmft_ipb' from anywhere, you can add the 'dist' directory to your PATH."

echo_info "You can do this by adding the following line to your ~/.zshrc or ~/.bashrc file:"
echo_info ""
echo_info "    export PATH=\"\$PATH:$PROJECT_DIR/dist\""
echo_info ""
echo_info "After adding the line, reload your shell configuration with:"
echo_info "    source ~/.zshrc   # If using Zsh"
echo_info "    source ~/.bashrc  # If using Bash"
echo_info ""
echo_info "Now you can run the executable from any directory using:"
echo_info "    dmft_ipb"
echo_info ""
echo_info "To start the DMFT loop, simply run:"
echo_info "    dmft_ipb"

echo_info ""
echo_info "Happy Computing!"