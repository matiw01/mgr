param(
    [Parameter(Mandatory=$true)]
    [string]$Dataset
)

#groq
#$models300 = @(
#    "llama-3.1-8b-instant",
#    "llama-3.3-70b-versatile",
#    "meta-llama/llama-4-scout-17b-16e-instruct",
#    "meta-llama/llama-prompt-guard-2-86m",
#    "meta-llama/llama-prompt-guard-2-22m",
#    "openai/gpt-oss-safeguard-20b",
#    "openai/gpt-oss-120b",
#    "openai/gpt-oss-20b",
#    "qwen/qwen3-32b",
#    "allam-2-7b"
#)

#openrouter
$models300 = @(
    "openrouter/elephant-alpha",
    "google/gemma-4-26b-a4b-it:free",
    "google/gemma-4-31b-it:free",
    "minimax/minimax-m2.5:free",
    "liquid/lfm-2.5-1.2b-thinking:free",
    "liquid/lfm-2.5-1.2b-instruct:free",
    "nvidia/nemotron-3-nano-30b-a3b:free",
    "nvidia/nemotron-nano-12b-v2-vl:free",
    "cognitivecomputations/dolphin-mistral-24b-venice-edition:free"
)

foreach ($model in $models300) {
    Write-Host "Running: $model on dataset: $Dataset"
    python -m research_first_step -m $model -p openrouter -d $Dataset --limit 300
}