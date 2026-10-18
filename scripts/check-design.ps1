$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$designRoot = Join-Path $projectRoot 'docs/design'
$styleRoot = Join-Path $projectRoot 'docs/style'
$required = @('README.md', 'workflow.md', 'valuation.md', 'execution.md')
$expectedSections = @('Problem Statement', 'Proposed Solution', 'Technical Details', 'Failure Handling', 'Validation', 'Not Implemented', 'Open Questions', 'References')
$issues = [Collections.Generic.List[string]]::new()

foreach ($name in $required) {
    if (-not (Test-Path -LiteralPath (Join-Path $designRoot $name) -PathType Leaf)) {
        $issues.Add("Missing design document: $name")
    }
}

$documents = @(Get-ChildItem -LiteralPath $designRoot -Filter '*.md' -Recurse)
$designPaths = @($documents.FullName)
if (-not (Test-Path -LiteralPath (Join-Path $styleRoot 'README.md') -PathType Leaf)) {
    $issues.Add('Missing style index: docs/style/README.md')
}
if (Test-Path -LiteralPath $styleRoot -PathType Container) {
    $documents += Get-ChildItem -LiteralPath $styleRoot -Filter '*.md' -Recurse
}
foreach ($name in @('README.md', 'AGENTS.md')) {
    $rootDocument = Join-Path $projectRoot $name
    if (Test-Path -LiteralPath $rootDocument -PathType Leaf) {
        $documents += Get-Item -LiteralPath $rootDocument
    } else {
        $issues.Add("Missing root $name")
    }
}

foreach ($document in $documents) {
    $content = [IO.File]::ReadAllText($document.FullName)
    if ($document.FullName -in $designPaths) {
        $sections = @([regex]::Matches($content, '(?m)^## (?<title>[^\r\n]+)') | ForEach-Object { $_.Groups['title'].Value })
        if (($sections -join '|') -cne ($expectedSections -join '|')) {
            $issues.Add("Common sections must appear exactly once in order: $($document.Name)")
        }
        $proseWithoutLinks = [regex]::Replace($content, '\[[^\]]+\]\([^)]+\)', '')
        if ($proseWithoutLinks -match '(?i)\bthis\s+(?:document|file|design)\b|\b(?:design documents?|documentation checker)\b') {
            $issues.Add("Document self-reference: $($document.Name)")
        }
        $missingFeatures = [regex]::Match($content, '(?ms)^## Not Implemented\r?\n(?<body>.*?)(?=^## |\z)')
        if (-not $missingFeatures.Success -or $missingFeatures.Groups['body'].Value -notmatch '(?m)^- ') {
            $issues.Add("Not Implemented must list absent features: $($document.Name)")
        }
    }
    if ([regex]::Matches($content, '(?m)^# ').Count -ne 1) {
        $issues.Add("Expected one document title: $($document.Name)")
    }
    if ([regex]::Matches($content, '(?m)^```').Count % 2 -ne 0) {
        $issues.Add("Unbalanced code fences: $($document.Name)")
    }
    if ($content -match '(?i)(?:chatgpt\.com|chat\.openai\.com)/(?:c|share)/|codex://(?:threads|chat)/') {
        $issues.Add("Conversation reference: $($document.Name)")
    }
    if ($content -match '(?i)(?:fixed|default|configurable)\s+10%|10%\s+(?:nominal USD equity hurdle|USD equity default|equity hurdle)') {
        $issues.Add("Retired fixed-rate policy: $($document.Name)")
    }
    if ($content -match '(?im)^dcf\s+|`dcf(?:\s|`)|\bsrc/dcf/') {
        $issues.Add("Retired console name: $($document.Name)")
    }
    if ($content -match '(?i)\bextraction_model\b|\bsummary\.md\b|smaller-agent summary|smaller-agent extraction|summary\.json|\.schema\.json') {
        $issues.Add("Retired extraction or schema contract: $($document.Name)")
    }
    if ($content -match '(?i)research --(?:resume|check|live)|\binspect <run-id>|--config\b|\bsnapshot\.json\b') {
        $issues.Add("Retired command, option or artifact: $($document.Name)")
    }
    foreach ($link in [regex]::Matches($content, '\[[^\]]+\]\((?<target>[^)]+)\)')) {
        $target = $link.Groups['target'].Value
        if ($target -match '^[a-zA-Z][a-zA-Z0-9+.-]*:') { continue }
        $parts = $target -split '#', 2
        $path = [Uri]::UnescapeDataString($parts[0])
        $resolved = if ($path) { Join-Path $document.DirectoryName $path } else { $document.FullName }
        if (-not (Test-Path -LiteralPath $resolved -PathType Leaf)) {
            $issues.Add("Broken local link in $($document.Name): $target")
            continue
        }
        if ($parts.Count -eq 2 -and $parts[1] -and [IO.Path]::GetExtension($resolved) -eq '.md') {
            $fragment = [Uri]::UnescapeDataString($parts[1])
            $linkedContent = [IO.File]::ReadAllText($resolved)
            $headingIds = @([regex]::Matches($linkedContent, '(?m)^#{1,6} (?<title>[^\r\n]+)') | ForEach-Object {
                $title = $_.Groups['title'].Value.Trim().ToLowerInvariant()
                $slug = [regex]::Replace($title, '[^\p{L}\p{N}_\-\s]', '')
                [regex]::Replace($slug, '\s', '-')
            })
            if ($headingIds -cnotcontains $fragment) {
                $issues.Add("Broken section link in $($document.Name): $target")
            }
        }
    }
}

$overviewPath = Join-Path $designRoot 'README.md'
if (Test-Path -LiteralPath $overviewPath -PathType Leaf) {
    $overview = [IO.File]::ReadAllText($overviewPath)
    $steps = @([regex]::Matches($overview, '(?m)^#### (?<step>\d+)\. ') | ForEach-Object { $_.Groups['step'].Value })
    if (($steps -join ',') -ne '1,2,3,4,5,6,7') {
        $issues.Add('Overview must explain seven pipeline steps in order')
    }
    $overviewBody = ($overview -split '(?m)^## References\r?$', 2)[0]
    foreach ($detail in @('workflow.md', 'valuation.md', 'execution.md')) {
        if ($overviewBody -notmatch ('\]\(' + [regex]::Escape($detail) + '(?:#[^)]+)?\)')) {
            $issues.Add("Overview must connect $detail to the pipeline outside References")
        }
    }
}

$workflowPath = Join-Path $designRoot 'workflow.md'
if (Test-Path -LiteralPath $workflowPath -PathType Leaf) {
    $workflow = [IO.File]::ReadAllText($workflowPath)
    $expectedCommands = @('research WMT [--model <model-id>] [--effort <level>]')
    $commandBlock = [regex]::Match($workflow, '(?ms)^### Commands\r?\n\s*```text\r?\n(?<commands>.*?)^```')
    $actualCommands = @($commandBlock.Groups['commands'].Value -split '\r?\n' | Where-Object { $_.Trim() } | ForEach-Object { $_.Trim() })
    if (-not $commandBlock.Success -or ($actualCommands -join '|') -cne ($expectedCommands -join '|')) {
        $issues.Add('Command examples must show the single research command with its model')
    }
    $expectedStages = @('initiation', 'research', 'modeling', 'refutation', 'comparison', 'review', 'report')
    $actualStages = @([regex]::Matches($workflow, '(?m)^\| `(?<stage>[^`]+)` \|') | ForEach-Object {
        $_.Groups['stage'].Value
    })
    if (($actualStages -join ',') -ne ($expectedStages -join ',')) {
        $issues.Add('Stage contracts must appear once each in the required order')
    }
    $expectedPrimary = @(
        'Valuation Summary',
        'Business Overview',
        'Competitive Moat',
        'Financial Analysis',
        'Outcome Formation',
        'Valuation Approach',
        'Outcome Distribution',
        'Risks and Sensitivities',
        'External Comparisons',
        'Sources and Calculations'
    )
    $rows = @([regex]::Matches($workflow, '(?m)^\| P(?<number>\d+) \| (?<name>[^|]+) \|'))
    $numbers = @($rows | ForEach-Object { $_.Groups['number'].Value })
    $names = @($rows | ForEach-Object { $_.Groups['name'].Value.Trim() })
    if (($numbers -join ',') -ne ((1..$expectedPrimary.Count) -join ',') -or
        ($names -join '|') -cne ($expectedPrimary -join '|')) {
        $issues.Add('Primary report sections must appear once each in the required order')
    }
    if ([regex]::Matches($workflow, '(?m)^### Outcome data\r?$').Count -ne 1) {
        $issues.Add('Workflow must define one outcome data contract')
    }
}

$ratePath = Join-Path $designRoot 'valuation.md'
if (Test-Path -LiteralPath $ratePath -PathType Leaf) {
    $rateDocument = [IO.File]::ReadAllText($ratePath)
    if ($rateDocument -notmatch '(?m)^r = treasury_10y_decimal \+ implied_erp_decimal\r?$') {
        $issues.Add('Missing common-hurdle formula')
    }
    foreach ($formula in @(
        'weighted_fair_value = sum(p_i * V_i)'
    )) {
        if (-not ($rateDocument -split '\r?\n').Contains($formula)) {
            $issues.Add("Missing agent weighting instruction: $formula")
        }
    }
}

if ($issues.Count) {
    $issues | ForEach-Object { Write-Output "FAIL: $_" }
    exit 1
}
Write-Output "PASS: $($documents.Count) documents; titles, fences, file/section links and consistency checks; design section templates, overview, command/stage order, report sections, formulas."
exit 0
