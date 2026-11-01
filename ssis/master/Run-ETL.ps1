param(
    [string]$SqlServer = 'localhost',
    [string]$RawDataDirectory,
    [switch]$SkipStaging,
    [string]$DtexecPath,
    [string]$PythonPath = 'python',
    [string]$OdbcDriver = 'ODBC Driver 17 for SQL Server'
)

$ErrorActionPreference = 'Stop'
$repositoryRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..\..')).Path
$masterPackage = Join-Path $PSScriptRoot 'Master_ETL.dtsx'
$csvLoader = Join-Path $repositoryRoot 'scripts\load_staging_csv.py'
$stagingIndexes = Join-Path $repositoryRoot 'sql\staging\03_create_staging_indexes.sql'

if (-not $DtexecPath) {
    $DtexecPath = (Get-Command dtexec.exe -ErrorAction Stop).Source
}
if (-not (Test-Path -LiteralPath $DtexecPath -PathType Leaf)) {
    throw "dtexec.exe not found: $DtexecPath"
}

if (-not $SkipStaging) {
    if (-not $RawDataDirectory) { throw 'Pass -RawDataDirectory or use -SkipStaging.' }
    $RawDataDirectory = (Resolve-Path -LiteralPath $RawDataDirectory).Path
    if (-not (Get-Command $PythonPath -ErrorAction SilentlyContinue)) { throw "Python not found: $PythonPath" }
    if (-not (Get-Command sqlcmd.exe -ErrorAction SilentlyContinue)) { throw 'sqlcmd.exe not found in PATH.' }
    if (-not (Test-Path -LiteralPath $csvLoader -PathType Leaf)) { throw "Missing CSV loader: $csvLoader" }
    if (-not (Test-Path -LiteralPath $stagingIndexes -PathType Leaf)) { throw "Missing index script: $stagingIndexes" }
}

if (-not (Test-Path -LiteralPath $masterPackage -PathType Leaf)) {
    throw "Missing package: $masterPackage"
}

if ($SqlServer -ne 'localhost') {
    throw 'These packages currently target localhost. Update their OLE DB connection managers before using another server.'
}

if (-not $SkipStaging) {
    Write-Host 'Loading UTF-8 CSVs into staging'
    & $PythonPath $csvLoader $RawDataDirectory --server $SqlServer --driver $OdbcDriver
    if ($LASTEXITCODE -ne 0) { throw "CSV staging load failed (exit $LASTEXITCODE)." }
    & sqlcmd -S $SqlServer -E -C -b -i $stagingIndexes
    if ($LASTEXITCODE -ne 0) { throw "Staging index/statistics update failed (exit $LASTEXITCODE)." }
}

Write-Host 'Loading and reconciling the data warehouse'
& $DtexecPath /F $masterPackage /REPORTING E
if ($LASTEXITCODE -ne 0) { throw "Master_ETL failed (exit $LASTEXITCODE)." }
Write-Host 'ETL completed successfully.'
