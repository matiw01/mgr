param(
    [Parameter(Mandatory=$true)]
    [string]$Dataset
)

$models300 = @(
    "llama-3.1-8b-instant",
    "llama-3.3-70b-versatile",
    "meta-llama/llama-4-scout-17b-16e-instruct",
    "meta-llama/llama-prompt-guard-2-86m",
    "meta-llama/llama-prompt-guard-2-22m",
    "openai/gpt-oss-safeguard-20b",
    "openai/gpt-oss-120b",
    "openai/gpt-oss-20b",
    "qwen/qwen3-32b",
    "allam-2-7b"
)

foreach ($model in $models300) {
    Write-Host "Running: $model on dataset: $Dataset"
    python -m research_first_step -m $model -p groq -d $Dataset --limit 300
}