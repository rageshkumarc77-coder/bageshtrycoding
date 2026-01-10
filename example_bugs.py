"""
Example file demonstrating common bug patterns for learning purposes
"""

def calculate_average(numbers):
    # BUG: Division by zero when list is empty
    return sum(numbers) / len(numbers)


def find_user(user_list, user_id):
    # BUG: Using mutable default argument
    for user in user_list:
        if user['id'] == user_id:
            return user
    return None


def process_data(data=[]):
    # BUG: Mutable default argument - list persists between calls
    data.append("new_item")
    return data


def compare_strings(str1, str2):
    # BUG: Using == for identity instead of equality
    if str1 is str2:
        return True
    return False


def read_file(filename):
    # BUG: File handle not properly closed
    file = open(filename, 'r')
    content = file.read()
    return content


# FIXED: Corrected off-by-one error
def get_last_n_items(items, n):
    # Returns the last n items from the list
    if n <= 0:
        return []
    return items[-n:]


if __name__ == "__main__":
    # Test the buggy functions
    print("Testing calculate_average:")
    print(calculate_average([1, 2, 3, 4, 5]))  # Works: 3.0
    # print(calculate_average([]))  # Would crash with ZeroDivisionError

    print("\nTesting process_data:")
    print(process_data())  # ['new_item']
    print(process_data())  # BUG: ['new_item', 'new_item'] - unexpected!

    print("\nTesting get_last_n_items:")
    print(get_last_n_items([1, 2, 3, 4, 5], 2))  # FIXED: Now correctly returns [4, 5]
