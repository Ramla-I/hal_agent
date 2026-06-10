import pandas as pd
import random
import re


def create_test_set(csv_file_path, start_row, end_row, keep_percentage, incorrect_value_percentage, incorrect_name_percentage=0):
    """
    Creates a test set from a CSV file with modified values for testing.
    
    Args:
        csv_file_path (str): Path to the input CSV file
        start_row (int): Start row index
        end_row (int): End row index
        keep_percentage (float): Percentage of rows to keep unchanged (0-100)
        incorrect_value_percentage (float): Percentage of rows to change (0-100)
        incorrect_name_percentage (float): Percentage of rows to have incorrect peripheral/register/field_name (0-100)
    
    Returns:
        pd.DataFrame: DataFrame with columns: peripheral, register, field_name, key, 
                     correct_value, and is_correct (True/False)
    
    Note:
        keep_percentage + incorrect_value_percentage + incorrect_name_percentage should equal 100
    """
    # Read the CSV file
    df = pd.read_csv(csv_file_path)
    
    df = df.iloc[start_row:end_row].reset_index(drop=True)
    
    # Keep only the specified columns
    columns_to_keep = ['peripheral', 'register', 'field_name', 'key', 'correct_value']
    df = df[columns_to_keep].copy()
    
    # Calculate number of rows to change
    total_rows = len(df)
    num_to_change = int(total_rows * incorrect_value_percentage / 100)
    num_incorrect_names = int(total_rows * incorrect_name_percentage / 100)
    
    # Initialize the is_correct column with True
    df['is_correct'] = True
    df['is_incorrect_name'] = False
    
    # Initialize list to track rows with incorrect names
    incorrect_name_indices = []
    
    # Randomly select rows to have incorrect names (peripheral, register, field_name)
    if num_incorrect_names > 0:
        incorrect_name_indices = random.sample(range(total_rows), num_incorrect_names)
        
        for idx in incorrect_name_indices:
            # Randomly pick one of peripheral, register, or field_name to replace with a random name
            name_column = random.choice(['peripheral', 'register', 'field_name'])
            df.loc[idx, name_column] = _generate_random_name()
            df.loc[idx, 'is_correct'] = False
            df.loc[idx, 'is_incorrect_name'] = True
    
    # Randomly select rows to change the value (excluding those already changed for names)
    if num_to_change > 0:
        # Get available indices (exclude those already changed for names)
        available_indices = [i for i in range(total_rows) if i not in incorrect_name_indices]
        # Sample from available indices, but don't exceed the number available
        num_to_change_actual = min(num_to_change, len(available_indices))
        if num_to_change_actual > 0:
            change_indices = random.sample(available_indices, num_to_change_actual)
            
            for idx in change_indices:
                # Change the correct_value randomly
                original_value = df.loc[idx, 'correct_value']
                new_value = _generate_random_value(original_value)
                df.loc[idx, 'correct_value'] = new_value
                df.loc[idx, 'is_correct'] = False
    
    return df


def _generate_random_name(length=None):
    """
    Generates a random name using a combination of letters.
    
    Args:
        length (int, optional): Desired length of the name. If None, uses random length between 3-12.
    
    Returns:
        str: A random string of letters
    """
    if length is None:
        length = random.randint(3, 12)
    
    # Generate random combination of letters
    letters = 'abcdefghijklmnopqrstuvwxyz'
    return ''.join(random.choice(letters) for _ in range(length))


def _generate_random_value(original_value):
    """
    Generates a random value based on the type of the original value.
    Ensures the new value is different from the original.
    
    Args:
        original_value: The original value (can be string, int, hex string, etc.)
    
    Returns:
        A randomly generated value of similar type that differs from the original
    """
    # Handle NaN or empty values
    if pd.isna(original_value) or original_value == '':
        return random.choice(['0', '0x0', '1', '0x1'])
    
    original_str = str(original_value).strip()
    
    # Check if it's a hex value (starts with 0x)
    hex_pattern = re.compile(r'^0x[0-9a-fA-F]+$')
    if hex_pattern.match(original_str):
        # Extract the hex number
        hex_num = int(original_str, 16)
        # Generate a random hex value that's different from the original
        # Keep it reasonable, within 0-0xFFFFFFFF
        max_val = min(0xFFFFFFFF, max(0xFF, hex_num * 2 + 10))
        while True:
            random_hex = random.randint(0, max_val)
            if random_hex != hex_num:
                return f'0x{random_hex:X}'
    
    # Check for access types like 'read-only', 'write-only', or 'read-write'
    if isinstance(original_value, str):
        access_types = ["read-only", "write-only", "read-write", "reserved"]
        if original_value in access_types:
            # Choose a new (different) access type at random
            access_options = [x for x in access_types if x != original_value]
            return random.choice(access_options).lower()

    # Check if it's a decimal number
    try:
        num_value = int(original_str)
        # Generate a random number that's different from the original
        # Keep it reasonable
        max_val = max(100, num_value * 2 + 10)
        while True:
            random_num = random.randint(0, max_val)
            if random_num != num_value:
                return str(random_num)
    
    except ValueError:
        # If it's not a number, return a random string or number
        return random.choice(['0', '1', '0x0', '0x1', str(random.randint(0, 100))])


def save_test_set(df, output_path):
    """
    Saves the test set DataFrame to a CSV file.
    
    Args:
        df (pd.DataFrame): The test set DataFrame
        output_path (str): Path where to save the CSV file
    """
    df.to_csv(output_path, index=False)
    print(f"Test set saved to {output_path}")


if __name__ == '__main__':
    # Example usage
    csv_path = 'verified_datasheet/stm/rm0041_stm32f100.csv'
    result_df = create_test_set(csv_path, start_row=1000, end_row=1500, keep_percentage=60, incorrect_value_percentage=30, incorrect_name_percentage=10)
    print(f"\nTotal rows: {len(result_df)}")
    print(f"Rows with is_correct=True: {result_df['is_correct'].sum()}")
    print(f"Rows with is_correct=False: {(~result_df['is_correct']).sum()}")
    
    # Uncomment to save the output
    save_test_set(result_df, 'test_set_output.csv')

