import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from ai_code_sandbox.sandbox import AICodeSandbox

def test_sandbox():
    sandbox = AICodeSandbox(packages=[])
    
    try:
        code = """
        print("Hello, world!")
        """
        
        result = sandbox.run_code(code)
        
        assert "Hello, world!" in result
    finally:
        sandbox.close()