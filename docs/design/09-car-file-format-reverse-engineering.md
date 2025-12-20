# Reverse engineering the .car file format (compiled asset catalogs)

Source:
- https://blog.timac.org/2018/1018-reverse-engineering-the-car-file-format/

## What it’s useful for
Background on **compiled asset catalogs** (`Assets.car`) and how CoreUI loads assets and variants. This connects directly to the “materials are recipes in `.car` files” idea.

## Key concepts (paraphrased)
- Asset catalogs compile into `.car` files at build time.
- CoreUI (private) retrieves best-matching renditions (scale, appearance, etc.).
- Tools like `assetutil` can introspect `.car` files (Apple internal tooling exists).

Short quote (under 25 words):
> “Asset catalogs… are compiled as car files.” (Timac blog)

## Why this matters for UI cloning
It explains why Apple’s materials and system visuals are:
- consistent
- versioned
- centrally defined
- hard to replicate with simple CSS blur

---
