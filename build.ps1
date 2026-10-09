$ErrorActionPreference = "Stop"

Push-Location $PSScriptRoot
try {
    $python = Get-Command python -ErrorAction Stop
    & $python.Source -m PyInstaller --noconfirm --clean --windowed --onedir `
        --name Wumpus --add-data "Imgs Wumpus;Imgs Wumpus" Wumpus.py
    if ($LASTEXITCODE -ne 0) {
        throw "PyInstaller terminó con código $LASTEXITCODE."
    }
    Write-Host "Aplicación lista en dist\Wumpus\Wumpus.exe"
}
finally {
    Pop-Location
}
