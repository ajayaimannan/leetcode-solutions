# Problem: 342. Power of Four
# Difficulty: Easy
# Language: Python
# Timestamp: "2026-02-07 10:25:46"

class Solution(object):
    def isPowerOfFour(self, n):
        if n<=0:
            return False
        while n%4==0:
            n=n//4
        return n==1
        """
        :type n: int
        :rtype: bool
        """
        