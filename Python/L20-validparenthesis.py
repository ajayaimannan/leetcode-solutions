class Solution(object):
    def isValid(self, s):
        stack=[]
        mapping={"]":"[",")":"(","}":"{"}
        for i in s :
            if i in mapping:
                top = stack.pop() if stack else "#"
                if mapping[i] != top:
                   return False
            else :
               stack.append(i)
        return not stack 
        """
        :type s: str
        :rtype: bool
        """
        