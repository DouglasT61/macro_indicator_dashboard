from pathlib import Path
import sys
import types

ROOT = Path(__file__).resolve().parents[1]
sys.modules.setdefault('brotli', types.ModuleType('brotli'))
sys.path[:0] = [str(ROOT / 'backend'), str(ROOT / 'vendor_py')]

import uvicorn

if __name__ == '__main__':
    uvicorn.run(
        'app.main:app',
        host='127.0.0.1',
        port=8005,
        access_log=False,
        log_config=None,
    )
