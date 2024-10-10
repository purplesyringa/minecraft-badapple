import json
import sys

total = 0

for line in sys.stdin:
    blocks = line.partition("//")[0].split()
    if not blocks:
        continue
    states = json.loads(blocks.pop())
    if blocks[0] == "[seethrough]":
        blocks.pop(0)
    count = len(blocks)
    for values in states.values():
        count *= len(values)
    total += count

print(total)
