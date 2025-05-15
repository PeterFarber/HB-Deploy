# HB Deploy

Deployment and management tool for HB servers.

## Features

- Server Configuration Management
- SSH Key Management with Persistent Agent
- Command Execution with Parallel Mode
- Release Building, Downloading, and Deployment
- Configuration Updates
- Parallel Command Execution with Retry Mechanism
- Interactive Shell with Tab Completion and Command History
- Command-Line Interface for Scripting
- Streamlined Logging with Color Support

## Installation

```bash
# Clone the repository
git clone https://github.com/permaweb/HB-Deploy.git
cd HB-Deploy

# Install dependencies
pip install -r requirements.txt
```

## Usage

### Interactive Menu Mode

```bash
./run
```

### Interactive Shell Mode

```bash
./run shell
```

### Command Line Mode

```bash
# Build a release
./run build

# Build a release on specific build servers
./run build --servers 8,9

# Download a release to all non-build servers
./run download

# Download a release to specific servers
./run download --servers 9,10

# Download a release to servers of a specific type
./run download --type router

# Start a release on all router and compute nodes
./run start

# Start a release on specific servers
./run start --servers 9,10

# Shutdown QEMU processes on all servers
./run shutdown

# Shutdown QEMU processes on specific servers
./run shutdown --servers 9,10

# Shutdown QEMU processes on servers of a specific type
./run shutdown --type compute

# Update configuration on all non-build servers
./run update-config

# Run a command on specific servers
./run run --servers 8,9,10 "uptime"

# Run a command on servers of a specific type
./run run --type compute "systemctl status nginx"

# Run a command in parallel mode
./run run --parallel --servers 8,9,10 "uptime"

# Run a command with custom timeout and retries
./run run --timeout 60 --retries 5 --servers 9,10 "sudo reboot"

# Specify max worker threads for parallel execution
./run run --parallel --max-workers 3 --servers 8,9,10,11,12 "uptime"
```

### SSH Key Management

The tool automatically manages your SSH keys:

- Remembers your last selected key between sessions
- Maintains a persistent SSH agent across multiple runs
- Automatically loads keys to avoid repeated passphrase prompts
- Secures the agent information for future use

### Server Selection

When running in interactive mode, you can select servers by:

- Individual server IDs: `9,10,11`
- Server type: `router`, `compute`, `build`, etc.
- Using `all` to select all servers

When using the command line, specify servers with:
- `--servers 9,10,11` for specific server IDs
- `--type router` for servers of a specific type

### Configuration

Configuration can be specified in multiple ways (in order of precedence):

1. Command-line arguments
2. Environment variables (prefixed with `HB_`)
3. Configuration files (`config.yaml`, `config.toml`, or `config.json`)
4. Default values

Example configuration file (`config.yaml`):

```yaml
server:
  user: hb
  config_file: ./config/servers.json

ssh:
  batch_mode: true
  identity_file: ~/.ssh/my_key

execution:
  parallel: true
  max_workers: 5
  retry_count: 3
  retry_delay: 5

logging:
  level: INFO
  file: ./hb-deploy.log
```

### Environment Variables

```bash
# Set logging level
export HB_LOGGING_LEVEL=DEBUG

# Enable parallel execution
export HB_EXECUTION_PARALLEL=true

# Set max workers for parallel execution
export HB_EXECUTION_MAX_WORKERS=10

# Specify SSH key to use
export HB_SSH_IDENTITY_FILE=~/.ssh/id_ed25519

# Run with environment variables
./run run --servers 8,9,10 "uptime"
```

### Command Arguments

All operations support these common options:

- `--parallel`: Execute commands in parallel
- `--max-workers N`: Set maximum worker threads for parallel execution
- `--timeout N`: Set command timeout in seconds
- `--retries N`: Set number of retry attempts for operations
- `--key PATH`: Specify SSH key file to use

Global options:

- `--log-level LEVEL`: Set logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- `--log-file PATH`: Set log file path
- `--config PATH`: Specify a custom configuration file
