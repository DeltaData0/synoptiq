"""Report fixture export until a frozen empirical asset exists."""

from _run_context import emit

emit("replay", "data/fixtures/replay_contract.json")
print("status=fixture")
print("note=No generated replay asset exists; serving fixture contract only.")

