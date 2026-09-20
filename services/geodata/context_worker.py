"""One context acquisition with an atomic completion file."""
import json
import os
import sys
from pathlib import Path

from services.geodata.context import city_context

if __name__ == '__main__':
    result = city_context(json.loads(Path(sys.argv[1]).read_text(encoding='utf-8')))
    response=Path(sys.argv[2])
    temporary=response.with_suffix('.partial')
    temporary.write_text(json.dumps(result), encoding='utf-8')
    os.replace(temporary,response)
