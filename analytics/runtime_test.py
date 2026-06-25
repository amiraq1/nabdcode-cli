def sum_mixed_numbers(mixed_list):
    total = 0
    for item in mixed_list:
        try:
            total += int(item)
        except ValueError:
            print(f"Warning: '{item}' is not a valid integer and will be ignored.")
    return total

if __name__ == "__main__":
    mixed_data = ['10', '20', 'bad_data', '30']
    result = sum_mixed_numbers(mixed_data)
    print(f"The sum of the valid numbers is: {result}")