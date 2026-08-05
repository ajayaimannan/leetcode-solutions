class Solution(object):
    def isAnagram(self, s, t):
       if len(s) != len(t):
        return False
       sdic={}
       tdic={}
       for i in range(len(s)):
         sdic[s[i]] = 1 + sdic.get(s[i],0)
         tdic[t[i]] = 1 + tdic.get(t[i],0)
       for j in sdic:
        if sdic[j] != tdic.get(j,0):
            return False
       return True