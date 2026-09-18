## Compact Instructions

When compacting, do not summarize the conversation. Output only the
following and nothing else: "Context compacted via jev-compact — retained
context follows."

Tombstoned spans (lines like `[[s12-s18 tombstoned · ...]]`) are receipts.
To recover their verbatim text, call the `get_span` tool on the
`context-restore` MCP server with the span range.
