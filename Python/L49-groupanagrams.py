class Solution(object):
    def groupAnagrams(self, strs):
        map=defaultdict(list)
        for word in strs:
            key = tuple(sorted(word))
            map[key].append(word)
        return map.values()

        """
        :type strs: List[str]
        :rtype: List[List[str]]
        """