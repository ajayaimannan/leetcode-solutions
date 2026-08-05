# Problem: 344. Reverse String
# Language: Python
# Timestamp: "2026-02-07 10:35:30"

class Solution(object):
    def reverseString(self, s):
        left=0
        right=len(s)-1
        while left<right:
            s[left],s[right] = s[right],s[left]
            left=left+1
            right=right-1
        """
        :type s: List[str]
        :rtype: None Do not return anything, modify s in-place instead.
        """
        