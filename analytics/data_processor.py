def process_data(data):
    if not isinstance(data, list):
        raise TypeError("Input must be a list")
    try:
        # Simulated data processing logic
        filtered_data = [item for item in data if item is not None]
        return filtered_data
    except TypeError:
        print("Ammar, the data filter caught a TypeError!")
        return None