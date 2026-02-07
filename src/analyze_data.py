import json
from collections import Counter
from pathlib import Path


def load_demagog_data(file_path):
    """Load data from demagog-data.json file."""
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return data


def analyze_data(data):
    """Analyze the data and count objects by class."""
    # Extract all class labels
    classes = [item['Class'] for item in data]

    # Count occurrences of each class
    class_counts = Counter(classes)

    # Calculate total number of objects
    total_objects = len(data)

    # Calculate percentages
    class_percentages = {
        cls: (count / total_objects) * 100
        for cls, count in class_counts.items()
    }

    return class_counts, class_percentages, total_objects


def print_analysis(class_counts, class_percentages, total_objects):
    """Print the analysis results in a formatted way."""
    print("=" * 60)
    print("ANALIZA DANYCH DEMAGOG")
    print("=" * 60)
    print(f"\nCałkowita liczba obiektów: {total_objects}")
    print("\n" + "-" * 60)
    print(f"{'Klasa':<30} {'Liczba':<15} {'Procent':<15}")
    print("-" * 60)

    # Sort by count (descending)
    for cls, count in sorted(class_counts.items(), key=lambda x: x[1], reverse=True):
        percentage = class_percentages[cls]
        print(f"{cls:<30} {count:<15} {percentage:>6.2f}%")

    print("-" * 60)


def main():
    # Path to the data file
    data_path = Path(__file__).parent.parent / 'data' / 'demagog-data.json'

    # Load data
    print("Ładowanie danych...")
    data = load_demagog_data(data_path)

    # Analyze data
    print("Analiza danych...")
    class_counts, class_percentages, total_objects = analyze_data(data)

    # Print results
    print_analysis(class_counts, class_percentages, total_objects)


if __name__ == "__main__":
    main()

