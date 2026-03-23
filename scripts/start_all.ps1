$backend = "$env:PYTHONPATH='backend;vendor_py'; python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload"
$frontend = "cd frontend; npm run dev -- --host 127.0.0.1 --port 5173"

Start-Process powershell -ArgumentList "-NoExit", "-Command", $backend
Start-Process powershell -ArgumentList "-NoExit", "-Command", $frontend
