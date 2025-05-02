# MCPTESTS

This is a test repository including a few of MCP examples.

## Quick Start on Mac

```bash
$ brew install uv

$ git clone https://github.com/appolloford/mcptests.git
$ cd mcptests
$ touch .env # save sensitive environment variables

$ uv venv
$ uv pip install .
```

### VSCode

- VSCode > v1.99.3 has to be installed and copilot is enabled
- Open this repository, select `agent` mode and start MCP servers

### Claude Desktop

- Claude Desktop has to be installed

```
$ sed "s|\${workspaceFolder}|$(pwd)|g" .vscode/mcp.json > ~/Library/Application\ Support/Claude/claude_desktop_config.json
```

### mcphost + ollama

- ollama has to be installed

```
$ brew install go
$ go install github.com/mark3labs/mcphost@latest
$ sed "s|\${workspaceFolder}|$(pwd)|g" .vscode/mcp.json > config.json
$ OLLAMA_CONTEXT_LENGTH=16384 $HOME/go/bin/mcphost -m ollama:llama3.2 --config config.json
```

### ollama weather client example

```
$ python src/client/ollama_weather_client.py src/server/weather.py
```

### vllm weather client example

1. Launch a vllm server

- `meta-llama/Llama-3.1-8B-Instruct`
```
$ echo 'HF_MODEL=meta-llama/Llama-3.1-8B-Instruct' >> .env && source .env
$ vllm serve $HF_MODEL --enable-auto-tool-choice --tool-call-parser llama3_json
```

- `neuralmagic/Llama-3.3-70B-Instruct-quantized.w8a8`
```
$ echo 'HF_MODEL=neuralmagic/Llama-3.3-70B-Instruct-quantized.w8a8' >> .env && source .env
$ vllm serve $HF_MODEL --tensor-parallel-size=4 --max-model-len=10000 --enable-auto-tool-choice --tool-call-parser llama3_json
```

2. Launch MCP server and client
```
$ python src/client/vllm_weather_client.py src/server/weather.py
```

### ollama c3se client + sse server example

1. Launch c3se MCP server via sse transport
```
$ python src/server/c3se.py --transport=sse
```

2. Launch client
```
$ python src/client/ollama_weather_client.py http://localhost:8395/sse
```

