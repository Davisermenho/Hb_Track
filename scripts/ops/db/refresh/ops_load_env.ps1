# HB_SCRIPT_KIND: OPS
# HB_SCRIPT_SIDE_EFFECTS: ENV_MODIFY
# HB_SCRIPT_SCOPE: infra
# HB_SCRIPT_IDEMPOTENT: YES
# HB_SCRIPT_ENTRYPOINT: . scripts/ops/db/refresh/_load_env.ps1
# HB_SCRIPT_OUTPUTS: env_vars

param(
  [string]$EnvPath = (Join-Path (Get-Location) ".env")
)

if (!(Test-Path $EnvPath)) {
  throw "Arquivo .env não encontrado em: $EnvPath"
}

Get-Content $EnvPath | ForEach-Object {
  $line = $_.Trim()
  if ($line.Length -eq 0) { return }
  if ($line.StartsWith("#")) { return }

  $parts = $line -split "=", 2
  if ($parts.Count -ne 2) { return }

  $name = $parts[0].Trim()
  $value = $parts[1].Trim()

  # remove aspas simples/duplas, se existirem
  if ((($value.StartsWith('"') -and $value.EndsWith('"')) -or ($value.StartsWith("'") -and $value.EndsWith("'")))) {
    $value = $value.Substring(1, $value.Length - 2)
  }

  [System.Environment]::SetEnvironmentVariable($name, $value, "Process")
}