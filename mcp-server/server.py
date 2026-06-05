# Novel2Screen MCP Server
# MCP protocol bridge for Novel2Screen workflow
import json
import sys
from ..backend.workflows.novel2screen import Novel2ScreenWorkflow
from ..backend.schemas.validator import validate_screenplay_yaml

workflow = Novel2ScreenWorkflow()

def handle_request(request: dict) -> dict:
    action = request.get("action", "")

    if action == "convert":
        novel_text = request.get("novel_text", "")
        title = request.get("title", "Untitled")
        genre = request.get("genre", "Drama")
        mode = request.get("mode", "")
        state = workflow.run(novel_text, title, genre, mode)
        return {"status": "ok", "result": state}

    elif action == "validate":
        yaml_str = request.get("yaml", "")
        valid, errors = validate_screenplay_yaml(yaml_str)
        return {"valid": valid, "errors": errors}

    else:
        return {"status": "error", "message": f"Unknown action: {action}"}


if __name__ == '__main__':
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            request = json.loads(line)
            response = handle_request(request)
            print(json.dumps(response), flush=True)
        except Exception as e:
            print(json.dumps({"status": "error", "message": str(e)}), flush=True)
