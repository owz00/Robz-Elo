import os

# Set your API key as a persistent environment variable:
#
# Windows Command Prompt (Run as Administrator):
#   setx CLAUDE_API_KEY "sk-ant-xxxx" /M
#   
# Windows PowerShell (Run as Administrator):
#   [Environment]::SetEnvironmentVariable("CLAUDE_API_KEY", "sk-ant-xxxx", "Machine")
#
# The /M flag (CMD) and "Machine" target (PowerShell) set it system-wide
# You'll need to restart your terminal for changes to take effect
#
# Linux/macOS Terminal:
#   sudo echo "export CLAUDE_API_KEY=sk-ant-xxxx" >> /etc/environment
#   source /etc/environment
#
API_KEYS = {
    'claude': os.getenv('CLAUDE_API_KEY', 'your-api-key-here')  # Replace 'your-api-key-here' if not using env var
}