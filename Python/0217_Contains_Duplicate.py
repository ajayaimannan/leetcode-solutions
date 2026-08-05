# Problem: 217. Contains Duplicate
# Language: Python
# Timestamp: "2026-02-02 09:55:04"

class Solution(object):
    def containsDuplicate(self, nums):
        seen = set()
        for num in  nums:
            if num in seen:
                return True
            else:
                seen.add(num)
        return False
        