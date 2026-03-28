SEED_PROBLEMS = [
    {
        "title": "Two Number Sum",
        "slug": "two-number-sum",
        "topic": "Arrays",
        "difficulty": "easy",
        "function_name": "two_sum",
        "description": """## Overview
Find two different positions in an integer list whose values add up to a target number.

Return the pair of indices in increasing order. You may assume exactly one valid answer exists for every test case in this practice set.

## Example 1
Input:
nums = [2, 7, 11, 15]
target = 9

Output:
[0, 1]

## Example 2
Input:
nums = [3, 2, 4]
target = 6

Output:
[1, 2]

## Constraints
- 2 <= len(nums) <= 10^4
- -10^9 <= nums[i], target <= 10^9
- Use the same element at most once
""",
        "starter_code": """def two_sum(nums, target):
    # Return the two indices as a list, for example [0, 1]
    pass
""",
        "visible_test_cases": [
            {"input": [[2, 7, 11, 15], 9], "expected_output": [0, 1], "explanation": "2 + 7 = 9"},
            {"input": [[3, 2, 4], 6], "expected_output": [1, 2], "explanation": "2 + 4 = 6"},
            {"input": [[3, 3], 6], "expected_output": [0, 1], "explanation": "The duplicated values are allowed"},
        ],
    },
    {
        "title": "Balanced Brackets",
        "slug": "balanced-brackets",
        "topic": "Stack",
        "difficulty": "easy",
        "function_name": "is_valid",
        "description": """## Overview
Given a string made only of parentheses, square brackets, and curly braces, decide whether the brackets are properly balanced.

A string is balanced when:
- every opening bracket is closed by the same type
- brackets close in the correct order

## Example 1
Input:
s = "()[]{}"

Output:
True

## Example 2
Input:
s = "(]"

Output:
False

## Constraints
- 1 <= len(s) <= 10^4
- s contains only the characters ()[]{}
""",
        "starter_code": """def is_valid(s):
    # Return True if the string is balanced, otherwise False
    pass
""",
        "visible_test_cases": [
            {"input": ["()[]{}"], "expected_output": True, "explanation": "Each opening bracket is matched correctly"},
            {"input": ["(]"], "expected_output": False, "explanation": "The closing bracket type does not match"},
            {"input": ["([{}])"], "expected_output": True, "explanation": "Nested brackets are allowed"},
        ],
    },
    {
        "title": "Binary Search Position",
        "slug": "binary-search-position",
        "topic": "Binary Search",
        "difficulty": "easy",
        "function_name": "search",
        "description": """## Overview
Given a sorted list of distinct integers and a target value, return the index where the target appears. If the target is missing, return -1.

The expected approach should run in logarithmic time.

## Example 1
Input:
nums = [-1, 0, 3, 5, 9, 12]
target = 9

Output:
4

## Example 2
Input:
nums = [-1, 0, 3, 5, 9, 12]
target = 2

Output:
-1

## Constraints
- 1 <= len(nums) <= 10^4
- nums is sorted in strictly increasing order
""",
        "starter_code": """def search(nums, target):
    # Return the index of target or -1 if it does not exist
    pass
""",
        "visible_test_cases": [
            {"input": [[-1, 0, 3, 5, 9, 12], 9], "expected_output": 4, "explanation": "9 is located at index 4"},
            {"input": [[-1, 0, 3, 5, 9, 12], 2], "expected_output": -1, "explanation": "2 is not in the list"},
            {"input": [[1, 3, 5, 7, 9], 1], "expected_output": 0, "explanation": "The target can be at the first position"},
        ],
    },
    {
        "title": "Best Profit From One Trade",
        "slug": "best-profit-from-one-trade",
        "topic": "Sliding Window",
        "difficulty": "easy",
        "function_name": "max_profit",
        "description": """## Overview
You are given daily stock prices. Choose one day to buy and a later day to sell. Return the largest profit you can make.

If no profitable trade exists, return 0.

## Example 1
Input:
prices = [7, 1, 5, 3, 6, 4]

Output:
5

## Example 2
Input:
prices = [7, 6, 4, 3, 1]

Output:
0

## Constraints
- 1 <= len(prices) <= 10^5
- 0 <= prices[i] <= 10^4
""",
        "starter_code": """def max_profit(prices):
    # Return the best profit from one buy followed by one sell
    pass
""",
        "visible_test_cases": [
            {"input": [[7, 1, 5, 3, 6, 4]], "expected_output": 5, "explanation": "Buy at 1 and sell at 6"},
            {"input": [[7, 6, 4, 3, 1]], "expected_output": 0, "explanation": "No profitable trade is possible"},
            {"input": [[2, 4, 1]], "expected_output": 2, "explanation": "Buy at 2 and sell at 4"},
        ],
    },
    {
        "title": "Contains Duplicate Value",
        "slug": "contains-duplicate-value",
        "topic": "Hashing",
        "difficulty": "easy",
        "function_name": "contains_duplicate",
        "description": """## Overview
Given a list of integers, return True if any value appears at least twice. Return False if all values are unique.

## Example 1
Input:
nums = [1, 2, 3, 1]

Output:
True

## Example 2
Input:
nums = [1, 2, 3, 4]

Output:
False

## Constraints
- 1 <= len(nums) <= 10^5
- -10^9 <= nums[i] <= 10^9
""",
        "starter_code": """def contains_duplicate(nums):
    # Return True if any value appears more than once
    pass
""",
        "visible_test_cases": [
            {"input": [[1, 2, 3, 1]], "expected_output": True, "explanation": "The value 1 appears twice"},
            {"input": [[1, 2, 3, 4]], "expected_output": False, "explanation": "Every value is unique"},
            {"input": [[1, 1, 1, 3, 3, 4, 3, 2, 4, 2]], "expected_output": True, "explanation": "Several values repeat"},
        ],
    },
]
