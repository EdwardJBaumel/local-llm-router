# Shared helpers — pip writes warnings to stderr; with $ErrorActionPreference Stop,
# PowerShell 5.x treats that as a terminating error unless we relax for native commands.

$global:LastPythonExitCode = 0

function Get-LastPythonExitCode {
    return [int]$global:LastPythonExitCode
}

function Invoke-Python {
    param([string[]]$PythonArgumentList)
    $prevEap = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    try {
        & python @PythonArgumentList
        if ($null -eq $LASTEXITCODE) {
            $global:LastPythonExitCode = 0
        } else {
            $global:LastPythonExitCode = [int]$LASTEXITCODE
        }
    } finally {
        $ErrorActionPreference = $prevEap
    }
}

function Invoke-Pip {
    param([string[]]$PipArgumentList)
    Invoke-Python -PythonArgumentList (@("-m", "pip") + $PipArgumentList)
}

function Uninstall-PipPackagesQuiet {
    param([string[]]$Packages)
    foreach ($pkg in $Packages) {
        Invoke-Python -PythonArgumentList @("-m", "pip", "show", $pkg)
        if ((Get-LastPythonExitCode) -ne 0) { continue }
        Write-Host "Removing installed $pkg ..." -ForegroundColor DarkGray
        Invoke-Pip -PipArgumentList @("uninstall", $pkg, "-y")
    }
}

function Assert-ExitCode {
    param(
        [int]$Code,
        [string]$Step
    )
    if ($Code -ne 0) {
        Write-Error "$Step failed (exit $Code)."
    }
}
