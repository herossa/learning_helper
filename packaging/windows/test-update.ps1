param(
    [Parameter(Mandatory = $true)][string]$InstallerA,
    [Parameter(Mandatory = $true)][string]$VersionA,
    [Parameter(Mandatory = $true)][string]$InstallerB,
    [Parameter(Mandatory = $true)][string]$VersionB,
    [string]$Port = "8765",
    [switch]$Force
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$tempRoot = if ($env:RUNNER_TEMP) { $env:RUNNER_TEMP } else { $env:TEMP }
$python = Join-Path $root ".venv\Scripts\python.exe"
if (!(Test-Path -LiteralPath $python)) {
    throw "Ambiente .venv nao encontrado. Rode 'uv sync --group dev' antes do teste."
}
Set-Location $root

function Write-Step {
    param([string]$Message)
    Write-Host "==> $Message"
}

function Get-InstalledApp {
    return Join-Path $env:LOCALAPPDATA "Programs\LearningHelper\learning-helper.exe"
}

function Get-InstalledVersion {
    param([string]$App)
    try {
        return (Get-Item -LiteralPath $App -ErrorAction Stop).VersionInfo.ProductVersion.Trim()
    } catch {
        return $null
    }
}

function Wait-InstalledVersion {
    param([string]$App, [string]$Expected, [int]$Seconds = 180)
    for ($i = 0; $i -lt $Seconds; $i++) {
        $version = Get-InstalledVersion -App $App
        if ($version -eq $Expected) {
            return $true
        }
        Start-Sleep -Seconds 1
    }
    return $false
}

function Stop-LearningHelper {
    Get-Process -Name "learning-helper" -ErrorAction SilentlyContinue |
        Stop-Process -Force -ErrorAction SilentlyContinue
}

function Write-SeedScript {
    param([string]$Path)
    Set-Content -LiteralPath $Path -Encoding UTF8 -Value @'
import sys
from learning_helper.persistence.db import Store, data_dir
from learning_helper.settings import Settings

store = Store()
settings = store.get_settings().to_dict()
settings["daily_usage_limit_seconds"] = 3600
store.save_settings(Settings(**settings))
store.insert_attempt(
    module_id="colors",
    level=1,
    prompt="teste",
    choices=["a", "b"],
    correct_answer="a",
    given_answer="a",
    is_correct=True,
)
store.complete_onboarding()
store.close()
print(data_dir())
'@
}

function Write-CheckScript {
    param([string]$Path)
    Set-Content -LiteralPath $Path -Encoding UTF8 -Value @'
import sys
from learning_helper.persistence.db import Store

store = Store()
settings = store.get_settings()
attempts = store.count_attempts()
store.close()
if settings.daily_usage_limit_seconds != 3600:
    raise SystemExit(f"limite diario inesperado: {settings.daily_usage_limit_seconds}")
if attempts < 1:
    raise SystemExit("tentativa de teste nao encontrada")
print(f"dados preservados: limite={settings.daily_usage_limit_seconds}, tentativas={attempts}")
'@
}

$installerA = (Resolve-Path -LiteralPath $InstallerA).Path
$installerB = (Resolve-Path -LiteralPath $InstallerB).Path
$distDir = Split-Path -Parent $installerB
$app = Get-InstalledApp
$appDir = Split-Path -Parent $app
if ((Test-Path -LiteralPath $appDir) -and !$Force) {
    throw "Ja existe uma instalacao em $appDir. Use -Force em uma maquina/VM de teste."
}
$testLocal = Join-Path $tempRoot "learning-helper-update-e2e"
$server = $null
$oldLocal = $env:LOCALAPPDATA
$oldUrl = $env:LEARNING_HELPER_UPDATE_URL
$oldNoUpdate = $env:LEARNING_HELPER_NO_UPDATE
$oldPythonPath = $env:PYTHONPATH

Write-Step "Versao A: $VersionA; versao B: $VersionB"

try {
    Write-Step "Instalando A"
    $install = Start-Process -FilePath $installerA -Wait -PassThru -ArgumentList @(
        "/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART", "/CURRENTUSER", "/SP-"
    )
    if ($install.ExitCode -ne 0) {
        throw "Falha ao instalar A (exit $($install.ExitCode))"
    }
    if (!(Test-Path -LiteralPath $app)) {
        throw "Aplicativo A nao encontrado em $app"
    }
    if ((Get-InstalledVersion -App $app) -ne $VersionA) {
        throw "Versao instalada de A nao confere"
    }

    Remove-Item -LiteralPath $testLocal -Recurse -Force -ErrorAction SilentlyContinue
    New-Item -ItemType Directory -Force -Path $testLocal | Out-Null
    $env:LOCALAPPDATA = $testLocal
    $env:PYTHONPATH = Join-Path $root "src"

    $seed = Join-Path $tempRoot "learning-helper-update-seed.py"
    $check = Join-Path $tempRoot "learning-helper-update-check.py"
    Write-SeedScript -Path $seed
    Write-CheckScript -Path $check
    & $python $seed
    if ($LASTEXITCODE -ne 0) {
        throw "Falha ao preparar o banco de teste"
    }

    Write-Step "Gerando manifesto local para B"
    & $python packaging/make_update_manifest.py `
        --version $VersionB `
        --dist $distDir `
        --base-url "http://127.0.0.1:$Port" `
        --assets windows_setup
    if ($LASTEXITCODE -ne 0) {
        throw "Falha ao gerar latest.json"
    }

    Write-Step "Servindo $distDir em http://127.0.0.1:$Port"
    $server = Start-Process -FilePath $python -WindowStyle Hidden -PassThru -ArgumentList @(
        "-m", "http.server", $Port, "--directory", $distDir
    )
    $ready = $false
    for ($i = 0; $i -lt 40; $i++) {
        try {
            $response = Invoke-WebRequest -UseBasicParsing `
                -Uri "http://127.0.0.1:$Port/latest.json" -TimeoutSec 1
            if ($response.StatusCode -eq 200) {
                $ready = $true
                break
            }
        } catch {
            Start-Sleep -Milliseconds 250
        }
    }
    if (!$ready) {
        throw "Servidor de atualizacao nao respondeu"
    }

    Write-Step "Aplicando atualizacao A -> B"
    $env:LEARNING_HELPER_UPDATE_URL = "http://127.0.0.1:$Port/latest.json"
    Remove-Item Env:LEARNING_HELPER_NO_UPDATE -ErrorAction SilentlyContinue
    $apply = Start-Process -FilePath $app -Wait -PassThru -ArgumentList "--apply-update"
    if ($apply.ExitCode -ne 0) {
        throw "Falha ao iniciar a atualizacao (exit $($apply.ExitCode))"
    }

    if (!(Wait-InstalledVersion -App $app -Expected $VersionB)) {
        throw "O aplicativo nao chegou a versao $VersionB"
    }

    $log = Join-Path $testLocal "learning_helper\updates\apply.log"
    $logReady = $false
    for ($i = 0; $i -lt 60; $i++) {
        if (Test-Path -LiteralPath $log) {
            $logContent = Get-Content -LiteralPath $log -Raw
            if ($logContent -match "Update applied|Update failed") {
                $logReady = $true
                break
            }
        }
        Start-Sleep -Seconds 1
    }
    if (!$logReady) {
        throw "O wrapper da atualizacao nao terminou a tempo"
    }

    Stop-LearningHelper
    Start-Sleep -Seconds 1

    Write-Step "Conferindo banco preservado"
    & $python $check
    if ($LASTEXITCODE -ne 0) {
        throw "Os dados de teste nao foram preservados"
    }

    Write-Host $logContent
    if ($logContent -notmatch "Installer exit code: 0") {
        throw "O instalador nao terminou com sucesso"
    }

    Write-Step "Testando rejeicao de SHA-256 invalido"
    $badManifest = @{
        version = "99.0.0"
        assets = @{
            windows_setup = @{
                name = (Split-Path -Leaf $installerB)
                url = "http://127.0.0.1:$Port/$(Split-Path -Leaf $installerB)"
                sha256 = ("0" * 64)
            }
        }
    }
    $badPath = Join-Path $distDir "latest-bad.json"
    $badManifest | ConvertTo-Json -Depth 6 |
        Set-Content -LiteralPath $badPath -Encoding ASCII

    $env:LEARNING_HELPER_UPDATE_URL = "http://127.0.0.1:$Port/latest-bad.json"
    $bad = Start-Process -FilePath $app -Wait -PassThru -ArgumentList "--apply-update"
    if ($bad.ExitCode -eq 0) {
        throw "Atualizacao com SHA-256 invalido foi aceita"
    }
    if ((Get-InstalledVersion -App $app) -ne $VersionB) {
        throw "O aplicativo mudou de versao depois de uma falha de SHA-256"
    }
    Write-Step "Falha de SHA-256 rejeitada corretamente"
} finally {
    Stop-LearningHelper
    if ($server -and !$server.HasExited) {
        Stop-Process -Id $server.Id -Force -ErrorAction SilentlyContinue
    }
    if ($oldLocal) { $env:LOCALAPPDATA = $oldLocal }
    if ($null -eq $oldUrl) { Remove-Item Env:LEARNING_HELPER_UPDATE_URL -ErrorAction SilentlyContinue }
    else { $env:LEARNING_HELPER_UPDATE_URL = $oldUrl }
    if ($null -eq $oldNoUpdate) { Remove-Item Env:LEARNING_HELPER_NO_UPDATE -ErrorAction SilentlyContinue }
    else { $env:LEARNING_HELPER_NO_UPDATE = $oldNoUpdate }
    if ($oldPythonPath) { $env:PYTHONPATH = $oldPythonPath }
    else { Remove-Item Env:PYTHONPATH -ErrorAction SilentlyContinue }

    if (Test-Path -LiteralPath $appDir) {
        $uninstaller = Get-ChildItem -LiteralPath $appDir -Filter "unins*.exe" -ErrorAction SilentlyContinue |
            Select-Object -First 1
        if ($uninstaller) {
            Start-Process -FilePath $uninstaller.FullName -Wait -ArgumentList @(
                "/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART"
            ) | Out-Null
        }
    }
}
