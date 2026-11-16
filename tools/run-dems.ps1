param(
    [string]$InputDir = "",
    [string]$Tag = ""
)

$ErrorActionPreference = "Continue"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$env:PYTHONIOENCODING = "utf-8"

$root = Split-Path -Parent $PSScriptRoot
$pipeline = Join-Path $root "dems_pipeline.py"
$outputRoot = Join-Path $root "output"

$localDeps = Join-Path $root "py_deps"
if (Test-Path -LiteralPath $localDeps) {
    if ($env:PYTHONPATH) {
        $env:PYTHONPATH = $localDeps + [IO.Path]::PathSeparator + $env:PYTHONPATH
    } else {
        $env:PYTHONPATH = $localDeps
    }
}

if (-not $env:MPLCONFIGDIR) {
    $env:MPLCONFIGDIR = Join-Path $root ".mplcache"
    New-Item -ItemType Directory -Force -Path $env:MPLCONFIGDIR | Out-Null
}

function Write-Step {
    param([string]$Text)
    Write-Host ""
    Write-Host ("===== " + $Text + " =====") -ForegroundColor Cyan
}

function Write-Problem {
    param([string]$Text)
    Write-Host $Text -ForegroundColor Yellow
}

function Resolve-Python {
    $candidates = @(
        @{ Command = "python"; Args = @() },
        @{ Command = "py"; Args = @("-3") },
        @{ Command = "$env:LOCALAPPDATA\Programs\Python\Python310\python.exe"; Args = @() },
        @{ Command = "$env:LOCALAPPDATA\Programs\Python\Python311\python.exe"; Args = @() },
        @{ Command = "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe"; Args = @() },
        @{ Command = "$env:USERPROFILE\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"; Args = @() },
        @{ Command = "$env:USERPROFILE\.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\python\python.exe"; Args = @() }
    )
    $fallback = $null
    foreach ($candidate in $candidates) {
        $found = [bool](Get-Command $candidate.Command -ErrorAction SilentlyContinue)
        if (-not $found -and (Test-Path -LiteralPath $candidate.Command -ErrorAction SilentlyContinue)) {
            $found = $true
        }
        if (-not $found) { continue }
        $previousPreference = $ErrorActionPreference
        $ErrorActionPreference = "Stop"
        try {
            & $candidate.Command $candidate.Args --version *> $null
            $ok = ($LASTEXITCODE -eq 0)
        } catch {
            $ok = $false
        } finally {
            $ErrorActionPreference = $previousPreference
        }
        if (-not $ok) { continue }
        # 优先选真正装了 numpy/matplotlib/yaml 的解释器
        $previousPreference = $ErrorActionPreference
        $ErrorActionPreference = "Stop"
        try {
            & $candidate.Command $candidate.Args -c "import numpy, matplotlib, yaml" *> $null
            $hasDeps = ($LASTEXITCODE -eq 0)
        } catch {
            $hasDeps = $false
        } finally {
            $ErrorActionPreference = $previousPreference
        }
        if ($hasDeps) { return $candidate }
        if (-not $fallback) { $fallback = $candidate }
    }
    return $fallback
}

function Get-DataFolder {
    Write-Step "选择 DEMS 数据文件夹"
    Write-Host "请把存放 HAL 原始 CSV 的文件夹拖到本窗口后按回车；也可以直接粘贴完整路径。"
    Write-Host "示例：D:\文档\Codex\科研\20261013-dems\dems"
    while ($true) {
        $raw = Read-Host "数据文件夹"
        if ($null -eq $raw) {
            Write-Problem "无法读取输入，请重新运行。"
            exit 1
        }
        $folder = $raw.Trim().Trim('"')
        if ($folder.EndsWith('\')) { $folder = $folder.Substring(0, $folder.Length - 1) }
        if ([string]::IsNullOrWhiteSpace($folder)) {
            Write-Problem "路径不能为空，请重新输入。"
            continue
        }
        if (-not (Test-Path -LiteralPath $folder)) {
            Write-Problem "找不到这个路径，请重新输入。"
            continue
        }
        $hasCsv = Get-ChildItem -LiteralPath $folder -Recurse -File -Filter "*.csv" -ErrorAction SilentlyContinue | Select-Object -First 1
        if (-not $hasCsv) {
            Write-Problem "这个文件夹里没有 .csv 文件，请重新输入。"
            continue
        }
        return (Resolve-Path -LiteralPath $folder).Path
    }
}

$pythonInfo = Resolve-Python
if (-not $pythonInfo) {
    Write-Problem "没有找到可用的 Python。请先安装 Python，并在安装时勾选 Add python.exe to PATH。"
    exit 1
}
$python = $pythonInfo.Command
$pythonArgs = $pythonInfo.Args

if ($InputDir) {
    if (-not (Test-Path -LiteralPath $InputDir)) {
        Write-Problem "找不到路径：$InputDir"
        exit 1
    }
    $inputDir = (Resolve-Path -LiteralPath $InputDir).Path
} else {
    $inputDir = Get-DataFolder
}

Write-Step "DEMS：识别周期峰、取段、出表、出图"
$scriptArgs = @(
    $pipeline,
    "--input-dir", $inputDir
)
if ($Tag) {
    $scriptArgs += @("--tag", $Tag)
}
if ($pythonArgs -and $pythonArgs.Count -gt 0) {
    & $python $pythonArgs $scriptArgs 2>&1 | Out-Host
} else {
    & $python $scriptArgs 2>&1 | Out-Host
}
$rc = $LASTEXITCODE
if ($rc -ne 0) {
    Write-Problem "DEMS 流程未完成，请检查窗口里的报错。"
    Write-Problem "放进去的 CSV 里要有以 Time 开头的表头行（如 Time,ms,Scan 1 : mass 32.00,...）。"
    exit 1
}

$best = Get-ChildItem -LiteralPath $outputRoot -Recurse -File -Filter "dems_best.csv" -ErrorAction SilentlyContinue |
    Sort-Object LastWriteTime -Descending |
    Select-Object -First 1
if (-not $best) {
    Write-Problem "没有找到 dems_best.csv，请检查窗口里的报错。"
    exit 1
}
$outDir = Split-Path -Parent $best.FullName

Write-Step "完成"
Write-Host "输出目录：$outDir"
Write-Host "图在 $outDir\图\，数据表在 $outDir\dems_best.csv。"
