# Fixed the "research" typo and using PowerShell loop
$models300 = @(
    "llama-3.1-8b-instant",
    "llama-3.3-70b-versatile",
    "meta-llama/llama-4-scout-17b-16e-instruct",
    "moonshotai/kimi-k2-instruct",
    "openai/gpt-oss-120b",
    "openai/gpt-oss-20b",
    "qwen/qwen3-32b",
    "allam-2-7b"
)

foreach ($model in $models300) {
    Write-Host "Running: $model"
    python -m research_first_step -m $model -p groq -d data/test.tsv --limit 300
}

$models250 = @(
    "groq/compound",
    "groq/compound-mini"
)

foreach ($model in $models250) {
    Write-Host "Running: $model"
    python -m research_first_step -m $model -p groq -d data/test.tsv --limit 250
}