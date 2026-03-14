"""Auto-generate API reference pages from the spunk source tree.

Runs at MkDocs build/serve time via the mkdocs-gen-files plugin.
For every public Python module under src/spunk/ it emits a virtual
.md file containing a single ``:::`` directive pointing at that module.
mkdocs-literate-nav then builds the nav from the generated SUMMARY.md.

Skipped:
  - ``__main__`` (not part of the public API)
  - Any module whose name starts with ``_`` (private internals)
"""
from __future__ import annotations

from pathlib import Path

import mkdocs_gen_files

SRC_ROOT = Path("src")
PKG_ROOT = SRC_ROOT / "spunk"

nav = mkdocs_gen_files.Nav()

for src_path in sorted(PKG_ROOT.rglob("*.py")):
    rel_to_src = src_path.relative_to(SRC_ROOT)       # spunk/resources/aws/dynamodb_table.py
    rel_to_pkg = src_path.relative_to(PKG_ROOT)        # resources/aws/dynamodb_table.py

    module_parts = list(rel_to_src.with_suffix("").parts)   # ["spunk", "resources", "aws", "dynamodb_table"]
    stem = module_parts[-1]

    # --- skip rules ----------------------------------------------------------
    if stem == "__main__":
        continue
    if stem.startswith("_") and stem != "__init__":
        continue

    # --- __init__ → treat as the package itself ------------------------------
    if stem == "__init__":
        module_parts = module_parts[:-1]
        doc_path = rel_to_pkg.parent / "index.md"
    else:
        doc_path = rel_to_pkg.with_suffix(".md")

    full_doc_path = Path("api") / doc_path
    module_ident = ".".join(module_parts)

    # nav key: path parts relative to the package, e.g. ("resources", "aws", "dynamodb_table")
    nav_parts = list(doc_path.with_suffix("").parts)

    with mkdocs_gen_files.open(full_doc_path, "w") as fd:
        fd.write(f"::: {module_ident}\n")

    mkdocs_gen_files.set_edit_path(full_doc_path, src_path)
    nav[nav_parts] = str(doc_path)

# Write the nav summary that mkdocs-literate-nav reads
with mkdocs_gen_files.open("api/SUMMARY.md", "w") as summary:
    summary.writelines(nav.build_literate_nav())
