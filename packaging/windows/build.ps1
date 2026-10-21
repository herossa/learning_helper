$ErrorActionPreference = "Stop"

$root = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
Set-Location $root

uv sync --frozen --group dev
if ($LASTEXITCODE -ne 0) { throw "uv sync falhou" }

$version = (uv run python -c "from learning_helper import __version__; print(__version__)").Trim()
$parts = @($version.Split(".") | ForEach-Object { [int]$_ })
while ($parts.Count -lt 4) { $parts += 0 }
$tuple = ($parts[0..3]) -join ", "

New-Item -ItemType Directory -Force build | Out-Null
$template = Get-Content packaging/windows/version_info.txt.in -Raw
$content = $template.Replace("@VERSION_TUPLE@", $tuple).Replace("@VERSION@", $version)
Set-Content -Path build/version_info.txt -Value $content -Encoding UTF8

uv run pyinstaller packaging/learning-helper.spec --noconfirm
if ($LASTEXITCODE -ne 0) { throw "PyInstaller falhou" }

& .\dist\learning-helper\learning-helper.exe --self-check
if ($LASTEXITCODE -ne 0) { throw "self-check do executável falhou" }

$iscc = (Get-Command iscc -ErrorAction SilentlyContinue).Source
if (-not $iscc) {
    $candidate = Join-Path ${env:ProgramFiles(x86)} "Inno Setup 6\ISCC.exe"
    if (Test-Path $candidate) {
        $iscc = $candidate
    } else {
        throw "ISCC.exe não encontrado. Instale o Inno Setup 6."
    }
}

& $iscc "/DAppVersion=$version" "/DSourceDir=$PWD\dist\learning-helper" packaging\windows\learning-helper.iss
if ($LASTEXITCODE -ne 0) { throw "ISCC falhou" }

Write-Host "Instalador gerado em dist\installer"
