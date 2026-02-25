#!/usr/bin/env python3
"""
Trigram Similarity Analysis for "part" Query

This script calculates trigram overlap manually to understand why
F1 search returns 0 results for the query "part".

PostgreSQL pg_trgm uses the following formula:
    similarity = (common_trigrams) / (total_unique_trigrams_in_both)

where trigrams are 3-character sequences including padding spaces.
"""

def generate_trigrams(text: str) -> set:
    """
    Generate trigrams for a string using PostgreSQL pg_trgm logic.

    PostgreSQL adds padding spaces: " text "
    Then extracts all 3-character windows.

    Example: "part" -> " part " -> ["  p", " pa", "par", "art", "rt "]
    """
    # Add padding spaces (PostgreSQL behavior)
    padded = f"  {text} "

    # Extract all 3-character windows
    trigrams = set()
    for i in range(len(padded) - 2):
        trigrams.add(padded[i:i+3])

    return trigrams


def calculate_similarity(query: str, target: str) -> float:
    """
    Calculate PostgreSQL pg_trgm similarity score.

    Formula: similarity = (common_trigrams) / (unique_trigrams_in_either)
    """
    query_trgm = generate_trigrams(query)
    target_trgm = generate_trigrams(target)

    common = query_trgm & target_trgm
    union = query_trgm | target_trgm

    if len(union) == 0:
        return 0.0

    return len(common) / len(union)


def analyze_query_variations():
    """Analyze mathematical normalization strategies for "part"."""

    query = "part"

    # Test cases from the requirements
    test_targets = [
        # Exact and close matches
        ("part", "Exact match"),
        ("parts", "x+1: Plural (adds 's')"),
        ("par", "x-1: Shorter by one"),

        # Compound terms (n±n)
        ("part_name", "Compound: part_name"),
        ("part_number", "Compound: part_number"),
        ("spare_part", "Compound: spare_part"),
        ("spare parts", "Compound: spare parts"),
        ("test part", "Compound: test part"),
        ("part for caterpillar", "Compound: part for caterpillar"),

        # Stemming variations
        ("parting", "Stem: parting"),
        ("parted", "Stem: parted"),
        ("partial", "Stem: partial"),

        # Real-world examples from failures.jsonl
        ("test part fa10ad48", "Real query: test part fa10ad48"),
        ("part for catepillar", "Real query: part for catepillar (misspelling)"),
        ("part for flter", "Real query: part for flter (misspelling)"),

        # Common inventory terms
        ("generator part", "Inventory: generator part"),
        ("engine parts", "Inventory: engine parts"),
        ("replacement part", "Inventory: replacement part"),
        ("parts inventory", "Inventory: parts inventory"),
    ]

    F1_THRESHOLD = 0.15
    DEFAULT_THRESHOLD = 0.3

    print("=" * 80)
    print("TRIGRAM SIMILARITY ANALYSIS: 'part'")
    print("=" * 80)
    print()

    # Show trigrams for "part"
    query_trgm = generate_trigrams(query)
    print(f"Query: '{query}'")
    print(f"Trigrams: {sorted(query_trgm)}")
    print(f"Trigram Count: {len(query_trgm)}")
    print()

    # Analyze each target
    print(f"{'Target':<30} {'Type':<35} {'Similarity':>10} {'F1 Pass':>10} {'Default Pass':>12}")
    print("-" * 100)

    results = []
    for target, description in test_targets:
        sim = calculate_similarity(query, target)
        f1_pass = "✓ YES" if sim >= F1_THRESHOLD else "✗ NO"
        default_pass = "✓ YES" if sim >= DEFAULT_THRESHOLD else "✗ NO"

        results.append({
            'target': target,
            'description': description,
            'similarity': sim,
            'f1_pass': sim >= F1_THRESHOLD,
            'default_pass': sim >= DEFAULT_THRESHOLD
        })

        print(f"{target:<30} {description:<35} {sim:>10.4f} {f1_pass:>10} {default_pass:>12}")

    print()
    print("=" * 80)
    print("SUMMARY STATISTICS")
    print("=" * 80)
    print()

    f1_passes = sum(1 for r in results if r['f1_pass'])
    default_passes = sum(1 for r in results if r['default_pass'])

    print(f"Total Targets Tested: {len(results)}")
    print(f"Pass F1 Threshold (0.15): {f1_passes} / {len(results)} ({f1_passes/len(results)*100:.1f}%)")
    print(f"Pass Default Threshold (0.3): {default_passes} / {len(results)} ({default_passes/len(results)*100:.1f}%)")
    print()

    # Find optimal threshold
    similarities = sorted([r['similarity'] for r in results if r['similarity'] > 0])
    if similarities:
        print("Similarity Distribution:")
        print(f"  Minimum: {min(similarities):.4f}")
        print(f"  Maximum: {max(similarities):.4f}")
        print(f"  Median: {similarities[len(similarities)//2]:.4f}")
        print()

        # Count how many would pass at different thresholds
        thresholds = [0.05, 0.10, 0.15, 0.20, 0.25, 0.30]
        print("Matches at Different Thresholds:")
        for threshold in thresholds:
            count = sum(1 for s in similarities if s >= threshold)
            pct = count / len(results) * 100
            print(f"  Threshold {threshold:.2f}: {count:>2} / {len(results)} ({pct:>5.1f}%)")

    print()
    print("=" * 80)
    print("DETAILED TRIGRAM BREAKDOWN (Top 5)")
    print("=" * 80)
    print()

    # Show detailed breakdown for top 5 targets
    sorted_results = sorted(results, key=lambda r: r['similarity'], reverse=True)[:5]
    for r in sorted_results:
        target_trgm = generate_trigrams(r['target'])
        common = query_trgm & target_trgm
        union = query_trgm | target_trgm

        print(f"Target: {r['target']}")
        print(f"  Query trigrams:  {sorted(query_trgm)}")
        print(f"  Target trigrams: {sorted(target_trgm)}")
        print(f"  Common:          {sorted(common)} ({len(common)})")
        print(f"  Union:           {len(union)} total trigrams")
        print(f"  Similarity:      {len(common)}/{len(union)} = {r['similarity']:.4f}")
        print()

    print("=" * 80)
    print("QUERY REWRITE RECOMMENDATIONS")
    print("=" * 80)
    print()

    # Suggest optimal rewrites
    top_variations = [
        ("part", 1.0, "Original query"),
        ("parts", 1.2, "x+1: Plural form - better trigram overlap"),
        ("spare part", 1.5, "n+n: Compound term - matches inventory language"),
        ("replacement part", 1.3, "n+n: Alternative phrasing"),
        ("part number", 1.4, "n+n: Common part identifier pattern"),
    ]

    print(f"{'Query Rewrite':<25} {'Weight':>8} {'Similarity':>12} {'Expected RRF Boost':>20} {'Reason':<40}")
    print("-" * 110)

    for rewrite, weight, reason in top_variations:
        # Calculate average similarity against common targets
        avg_sim = sum(calculate_similarity(rewrite, t) for t, _ in test_targets[:10]) / 10
        rrf_boost = weight * avg_sim

        print(f"{rewrite:<25} {weight:>8.1f}x {avg_sim:>12.4f} {rrf_boost:>20.4f} {reason:<40}")

    print()
    print("=" * 80)
    print("POSTGRESQL FTS STOP WORD CHECK")
    print("=" * 80)
    print()

    # Note: This would require actual DB connection
    print("⚠ WARNING: 'part' may be a stop word in PostgreSQL English FTS")
    print()
    print("To verify, run this SQL:")
    print("  SELECT to_tsvector('english', 'part');")
    print()
    print("If result is empty (''), then 'part' IS a stop word.")
    print("This would cause Full-Text Search (FTS) to return 0 results.")
    print()
    print("SOLUTION:")
    print("  1. Use 'simple' text search config instead of 'english'")
    print("  2. OR generate query rewrites: 'parts', 'spare part', etc.")
    print("  3. OR rely on trigram + vector embeddings only")
    print()


def calculate_optimal_boost_factors():
    """Calculate optimal term weight/boost factors."""

    print("=" * 80)
    print("BOOST FACTOR CALCULATIONS (RRF Context)")
    print("=" * 80)
    print()

    # RRF formula: score = 1/(k + rank) for each signal
    # With k=60, rank 1 contributes 1/61 = 0.0164

    RRF_K = 60

    query_variations = [
        ("part", 1.0),
        ("parts", 1.2),
        ("spare part", 1.5),
        ("part number", 1.3),
    ]

    print("Assuming each rewrite has different expected ranking positions:")
    print()
    print(f"{'Rewrite':<20} {'Weight':>8} {'Rank 1 Contrib':>16} {'Rank 5 Contrib':>16} {'Rank 10 Contrib':>17}")
    print("-" * 80)

    for rewrite, weight in query_variations:
        rank1 = weight * (1.0 / (RRF_K + 1))
        rank5 = weight * (1.0 / (RRF_K + 5))
        rank10 = weight * (1.0 / (RRF_K + 10))

        print(f"{rewrite:<20} {weight:>8.1f}x {rank1:>16.6f} {rank5:>16.6f} {rank10:>17.6f}")

    print()
    print("Interpretation:")
    print("  - Higher weight increases RRF score contribution")
    print("  - Weight 1.5x means 50% boost to fusion score")
    print("  - Compound terms (n+n) should get higher weights")
    print("  - Plural forms (x+1) should get moderate boost (1.2x)")
    print()


if __name__ == "__main__":
    analyze_query_variations()
    print()
    calculate_optimal_boost_factors()

    print()
    print("=" * 80)
    print("NEXT STEPS")
    print("=" * 80)
    print()
    print("1. Run test_part_search_debug.sql to verify FTS stop word status")
    print("2. Check if vector embeddings capture semantic similarity for 'part'")
    print("3. Implement query rewriter to generate variations:")
    print("   - 'part' -> ['part', 'parts', 'spare part', 'part number']")
    print("4. Consider lowering trigram threshold from 0.15 to 0.10")
    print("5. Add 'part' to learned_keywords for relevant entities")
    print()
