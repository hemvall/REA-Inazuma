"""Generate client snippets for this checkout without changing global settings."""
import json
from pathlib import Path


def main():
    root=Path(__file__).resolve().parents[1]
    executable=root/'local/agent-venv/Scripts/python.exe'
    if not executable.is_file():raise SystemExit('Exécutez d’abord Installer MCP.cmd.')
    server={'command':str(executable),'args':[str(root/'src/mcp_server.py')]}
    folder=root/'build';folder.mkdir(exist_ok=True)
    json_path=folder/'mcp-client.json'
    toml_path=folder/'mcp-codex.toml'
    json_path.write_text(json.dumps({'mcpServers':{'inazumia':server}},indent=2),encoding='utf-8')
    toml_path.write_text('[mcp_servers.inazumia]\ncommand = '+json.dumps(server['command'])+
                        '\nargs = '+json.dumps(server['args'])+'\n',encoding='utf-8')
    print('Configuration MCP JSON : '+str(json_path))
    print('Configuration Codex TOML : '+str(toml_path))


if __name__=='__main__':main()
