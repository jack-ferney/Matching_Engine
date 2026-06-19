<#
.SYNOPSIS
    Run the matching-engine benchmark multiple times and report averaged stats.
.DESCRIPTION
    Discards one warm-up run (cold cache / first-touch allocations), then runs the
    benchmark $Runs times and reports avg / median / min / max / sd for throughput
    and the latency percentiles. Produces the numbers quoted in the README.
.EXAMPLE
    .\scripts\bench.ps1                       # 12 runs, 2,000,000 orders
    .\scripts\bench.ps1 -Runs 20 -N 5000000
#>
param(
    [int]$Runs = 12,
    [long]$N = 2000000,
    [string]$Exe = "build\bench.exe"
)

if ($Exe -notmatch '[\\/]') { $Exe = Join-Path '.' $Exe }   # bare name -> run from cwd
if (-not (Test-Path $Exe)) {
    Write-Error "benchmark not found at $Exe -- build it first: cmake --build build"
    exit 1
}

& $Exe $N | Out-Null    # discarded warm-up run

$thr = @(); $p50 = @(); $p99 = @(); $p999 = @()
for ($i = 0; $i -lt $Runs; $i++) {
    $out = & $Exe $N
    foreach ($line in $out) {
        if     ($line -match 'throughput.*:\s*([\d.]+)') { $thr  += [double]$Matches[1] }
        elseif ($line -match 'p99\.9.*:\s*([\d.]+)')     { $p999 += [double]$Matches[1] }
        elseif ($line -match 'p99 .*:\s*([\d.]+)')       { $p99  += [double]$Matches[1] }
        elseif ($line -match 'p50.*:\s*([\d.]+)')        { $p50  += [double]$Matches[1] }
    }
}

function Stat($a) {
    $m = $a | Measure-Object -Average -Minimum -Maximum
    $s = $a | Sort-Object
    $median = if ($a.Count % 2) { $s[[int]($a.Count / 2)] }
              else { ($s[$a.Count / 2 - 1] + $s[$a.Count / 2]) / 2 }
    $var = 0; foreach ($x in $a) { $var += [math]::Pow($x - $m.Average, 2) }
    "avg {0,13:N1}  median {1,13:N1}  min {2,12:N1}  max {3,12:N1}  sd {4,10:N1}" -f `
        $m.Average, $median, $m.Minimum, $m.Maximum, [math]::Sqrt($var / $a.Count)
}

Write-Host ("measured runs : {0}  (after 1 warm-up), N = {1:N0}" -f $Runs, $N)
Write-Host ("throughput o/s: " + (Stat $thr))
Write-Host ("p50  (ns)     : " + (Stat $p50))
Write-Host ("p99  (ns)     : " + (Stat $p99))
Write-Host ("p99.9 (ns)    : " + (Stat $p999))
