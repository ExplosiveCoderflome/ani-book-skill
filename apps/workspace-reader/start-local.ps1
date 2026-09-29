param(
    [string[]]$Roots = @(),
    [switch]$Dev,
    [int]$Port = 8790
)
$ErrorActionPreference = 'Stop'
Push-Location -LiteralPath $PSScriptRoot
try {
    if ($Roots.Count -gt 0) {
        $resolvedRoots = @($Roots | ForEach-Object { (Resolve-Path -LiteralPath $_).Path })
        $env:ANI_READER_ROOTS = ConvertTo-Json -Compress -InputObject $resolvedRoots
    }
    if (-not (Test-Path -LiteralPath 'node_modules/.bin/react-router.cmd')) {
        & npm.cmd ci --include=dev --no-audit --no-fund
        if ($LASTEXITCODE -ne 0) { throw '阅读台依赖安装失败。' }
    }
    if ($Dev) {
        & npm.cmd run dev -- --port $Port
    } else {
        & npm.cmd run build
        if ($LASTEXITCODE -ne 0) { throw '阅读台构建失败。' }
        $env:PORT = "$Port"
        & node server.mjs
    }
    if ($LASTEXITCODE -ne 0) { throw '阅读台启动失败。' }
} finally {
    Pop-Location
}
