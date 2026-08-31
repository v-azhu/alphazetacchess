from pathlib import Path
import re

SEARCH = Path("src/alphazetacchess/engine/search.py")
text = SEARCH.read_text(encoding="utf-8")

# Constructor parameter.
if "use_mobility=False" not in text:
    needle = "        use_piece_square_tables=True,\n        use_king_safety=True,\n        tt_max_entries=200_000,\n"
    replacement = (
        "        use_piece_square_tables=True,\n"
        "        use_king_safety=True,\n"
        "        use_mobility=False,\n"
        "        mobility_weight=1,\n"
        "        tt_max_entries=200_000,\n"
    )
    if needle not in text:
        raise SystemExit("Constructor patch point not found.")
    text = text.replace(needle, replacement, 1)

# Constructor state.
if "self.use_mobility = use_mobility" not in text:
    needle = "        self.use_king_safety = use_king_safety\n        self.nodes_evaluated = 0\n"
    replacement = (
        "        self.use_king_safety = use_king_safety\n"
        "        # V0.4.3: optional Mobility evaluation term.\n"
        "        # Disabled by default to preserve the V0.4.2 baseline.\n"
        "        self.use_mobility = use_mobility\n"
        "        self.mobility_weight = mobility_weight\n"
        "        self.nodes_evaluated = 0\n"
    )
    if needle not in text:
        raise SystemExit("Constructor state patch point not found.")
    text = text.replace(needle, replacement, 1)

# Forward the two options at every evaluation call.  The current V0.4.2
# search.py has four evaluation call sites, but their indentation differs,
# so use a line-based replacement instead of an indentation-sensitive block.
pattern = r"^(\s*)use_king_safety=self\.use_king_safety,\s*$"
matches = list(re.finditer(pattern, text, re.MULTILINE))
if len(matches) != 4:
    raise SystemExit(
        f"Expected 4 evaluate() call sites using use_king_safety, found {len(matches)}. "
        "No file was written."
    )

lines = text.splitlines(keepends=True)
out = []
for line in lines:
    out.append(line)
    if re.match(pattern, line):
        indent = re.match(pattern, line).group(1)
        # Do not duplicate the arguments if the script is re-run.
        out.append(f"{indent}use_mobility=self.use_mobility,\n")
        out.append(f"{indent}mobility_weight=self.mobility_weight,\n")

text = "".join(out)
SEARCH.write_text(text, encoding="utf-8")
print("V0.4.3-beta-2 SearchEngine integration applied successfully.")
print("Updated 4 evaluate() call sites.")
