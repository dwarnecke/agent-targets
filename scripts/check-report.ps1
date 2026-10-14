param([Parameter(ValueFromRemainingArguments = $true)][string[]]$Path)

$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
if (-not $Path) {
    $Path = @(Get-ChildItem -LiteralPath (Join-Path $projectRoot 'runs') -Filter 'report.md' -Recurse | ForEach-Object FullName)
}

$sections = @('Valuation Summary', 'Business Overview', 'Competitive Moat', 'Financial Analysis', 'Outcome Formation', 'Valuation Approach', 'Outcome Distribution', 'Risks and Sensitivities', 'External Comparisons', 'Sources and Calculations')
# Process words that no business sentence needs
$leaks = '(?i)powershell|command line|report file|saved record|preserved (?:calculation )?record|original model|independent (?:review|valuation|checks?)'
$failed = $false

foreach ($file in $Path) {
    $lines = [IO.File]::ReadAllLines($file)
    $issues = [Collections.Generic.List[string]]::new()

    $headings = @(for ($i = 0; $i -lt $lines.Count; $i++) { if ($lines[$i] -match '^#{1,3}\s') { [pscustomobject]@{ Line = $i + 1; Text = $lines[$i] } } })
    $previous = 0
    $starts = @{}
    foreach ($section in $sections) {
        $found = $headings | Where-Object { $_.Line -gt $previous -and $_.Text -match [regex]::Escape($section) } | Select-Object -First 1
        if (-not $found) {
            $issues.Add("Section missing or out of order: $section")
        } else {
            $previous = $found.Line
            $starts[$section] = $found.Line
        }
    }

    if ($starts['Valuation Summary'] -and $starts['Business Overview']) {
        $summary = $lines[($starts['Valuation Summary'])..($starts['Business Overview'] - 2)]
        if (-not ($summary | Where-Object { $_ -match '^\|.*probabilit' })) {
            $issues.Add('Valuation Summary has no outcome table with a probability column')
        }
        if ($summary | Where-Object { $_ -match '^\|\s*\**[A-Z]{1,2}\d+\**\s*\|' }) {
            $issues.Add('Valuation Summary names an outcome by its ID')
        }
    }

    for ($i = 0; $i -lt $lines.Count; $i++) {
        if ($lines[$i] -match '\\\(|\\\[') { $issues.Add("Line $($i + 1): \( or \[ math delimiter") }
        if ($lines[$i] -match $leaks) { $issues.Add("Line $($i + 1): process wording '$($Matches[0])'") }
        if ($lines[$i] -match '\\\$[1-9]\d*\.\d{4,}') { $issues.Add("Line $($i + 1): unrounded dollar value '$($Matches[0])'") }
    }

    $label = Split-Path -Leaf (Split-Path -Parent $file)
    if ($issues.Count) {
        $failed = $true
        Write-Output "FAIL: $label"
        $issues | ForEach-Object { Write-Output "  $_" }
    } else {
        Write-Output "PASS: $label"
    }
}

if ($failed) { exit 1 }
