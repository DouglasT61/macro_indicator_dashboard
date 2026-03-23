param(
  [string]$ListenHost = '127.0.0.1',
  [int]$Port = 5173
)

Push-Location frontend
try {
  npm run dev -- --host $ListenHost --port $Port
}
finally {
  Pop-Location
}
