"""Save precomputed fixture for compare mode between freelance_v1 and freelance_v2."""
import json
from pathlib import Path
import sys

root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root))

from app.agents.segmenter import _heuristic_segment
from app.agents.comparator import align_clauses, analyze_clause_pair_heuristic

samples_dir = root.parent / "samples"
fixtures_dir = root / "app" / "fixtures"

p1 = (samples_dir / "freelance_v1.txt").read_text(encoding="utf-8")
p2 = (samples_dir / "freelance_v2.txt").read_text(encoding="utf-8")

ca = [{"id": f"a_{c.ordinal}", "ordinal": c.ordinal, "heading": c.heading, "text": c.text} for c in _heuristic_segment(p1)]
cb = [{"id": f"b_{c.ordinal}", "ordinal": c.ordinal, "heading": c.heading, "text": c.text} for c in _heuristic_segment(p2)]

aligned = align_clauses(ca, cb)
pairs = [analyze_clause_pair_heuristic(a, b).model_dump() for a, b in aligned]
worse = [p for p in pairs if p["risk_delta"] == "worse"]
bottom_line = [f"• {p['what_changed']} (Who benefits: {p['who_benefits']})" for p in worse[:5]]
while len(bottom_line) < 5:
    bottom_line.append("• Review all marked clauses carefully before agreeing to new revisions.")

data = {
    "pairs": pairs,
    "bottom_line": bottom_line,
}

fixture_path = fixtures_dir / "07fc38aeb94867ff_5d058be49aa9c125__compare.json"
fixture_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
print(f"Saved compare fixture to {fixture_path} ({len(pairs)} pairs, {len(worse)} worse)")
