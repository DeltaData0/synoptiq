"""Report the real-data pilot gate without fetching or inventing source keys."""

from _run_context import emit

emit("pilot", "docs/data_audit.md")
print("status=blocked")
print("reason=No inventoried GEFSv12/IMD source files. Fixture mode remains active.")

