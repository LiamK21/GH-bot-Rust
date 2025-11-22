#!/bin/bash

# Check if Python 3.12 is installed
python3.12 --version >/dev/null

if [ $? -ne 0 ]; then
    echo "Python 3.12 is not installed. Please install Python 3.12 and try again."
    exit 1
fi

# Retrieve absolute path to cli script
TARGET_DIR="$( cd "$( dirname "$0")" &&  pwd)"
CLI_SCRIPT_PATH="$TARGET_DIR/cli.py"

# Retrieve current shell by checking parent process ID
# This should always give the correct shell no matter how the script is invoked
# ./test.sh --> bash/zsh | bash/zsh test.sh --> bash/zsh
CURRENT_SHELL=$(ps -p $PPID -o comm=)

# Strip path if present (e.g., /bin/bash -> bash)
CURRENT_SHELL="${CURRENT_SHELL##*/}"

# Determine shell config file (ATM only bash and zsh)
if [[ "$CURRENT_SHELL" == "zsh" ]]; then
    SHELL_CONFIG="$HOME/.zshrc"
elif [[ "$CURRENT_SHELL" == "bash" ]]; then
    SHELL_CONFIG="$HOME/.bashrc"
else
    echo "Could not detect active shell (detected: $CURRENT_SHELL). Defaulting to .bashrc"
    SHELL_CONFIG="$HOME/.bashrc"
fi

# Prepare the alias command to add
ALIAS_CMD="alias testgen='python3.12 $CLI_SCRIPT'"

# Check if the alias already exists in the shell config
if grep -Fxq "$ALIAS_CMD" "$SHELL_CONFIG"; then
    echo "Alias 'testgen' already exists in $SHELL_CONFIG"

# Else, append the alias to the shell config
else 
    echo "" >> "$SHELL_CONFIG"
    echo "# Added by GH-Bot-Rust installer" >> "$SHELL_CONFIG"
    echo "$ALIAS_CMD" >> "$SHELL_CONFIG"
    echo "Alias 'testgen' added to $SHELL_CONFIG"
    echo "Please source $SHELL_CONFIG"
fi

# Make the python script executable
chmod +x "$CLI_SCRIPT"

# Remove .git directory 
rm -rf "$TARGET_DIR/.git"

# Run command to verify installation and setup GH-Bot-Rust
testgen --config