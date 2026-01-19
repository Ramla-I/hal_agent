import tiktoken
import os
import sys
import json

# HACK, remove this once we have a proper package structure
# Add the parent directory to sys.path
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(parent_dir)

from utils.models import model_costs

responses_roles = ["user", "developer", "assistant"]
expected_output_tokens = 10_000
expected_reasoning_tokens = 500
encoding_name = "cl100k_base"

def normalize_responses_input(input_list: list) -> list:
    """
    Convert Responses API message / output objects into JSON-serializable
    {role: 'user/ developer/ assistant', content:"..."} dicts.
    """
    normalized = []

    for msg in input_list: # take individiual message with a distinct role

        ## Let's just always normalize the input just in case some inputs are not text
        # # Already normalized
        # if isinstance(msg, dict):
        #     normalized.append(msg)
        #     continue

        # Responses API message object
        role = msg.get("role", "none")
        if role not in responses_roles:
            print("Interesting...Role is not in the list of allowed roles, just set to user: ", role)
            role = "user"
        
        content = msg.get("content", "")
        # content is a string

        if content:
            normalized.append({
                "role": role,
                "content": content
            })

    return normalized

def count_tokens(msgs: list) -> int:
    encoding = tiktoken.get_encoding(encoding_name)
    total = 0
    for msg in msgs:
        json_msg = json.dumps(msg)
        total += len(encoding.encode(json_msg))
    return total


def truncate_message_by_tokens(
    input_list: list,
    model_name: str,
    max_tokens: int | None = None,
) -> (bool, list):
    """
    Truncate messages to fit within max_tokens.
    Strategy:
      1. Walk messages from last → first
      2. First truncate message content
      3. If content becomes empty, remove message
    """

    messages = normalize_responses_input(input_list)

    if max_tokens is None:
        max_tokens = (
            model_costs[model_name]["window"]
            - expected_output_tokens
            - expected_reasoning_tokens
        )

    if not messages or max_tokens <= 0:
        return False, []

    encoding = tiktoken.get_encoding(encoding_name)
    truncated = [msg.copy() for msg in messages]

    def total_tokens():
        return count_tokens(truncated)

    # Fast path
    if total_tokens() <= max_tokens:
        return False, truncated

    print("Too many tokens, truncating... original number of tokens:", total_tokens(), " Requested max tokens:", max_tokens)

    msg_index = len(truncated) - 1

    while msg_index >= 0 and total_tokens() > max_tokens:
        msg = truncated[msg_index]
        content = msg.get("content", "")

        if isinstance(content, str) and content:
            tokens = encoding.encode(content)
            overflow = total_tokens() - max_tokens

            if overflow >= len(tokens):
                # Removing entire content is not enough → drop message
                truncated.pop(msg_index)
            else:
                # Truncate only the required number of tokens
                keep = len(tokens) - overflow
                msg["content"] = encoding.decode(tokens[:keep])
                break # we've found the message to truncate

        else:
            # Empty or non-text content → remove message
            truncated.pop(msg_index)

        msg_index -= 1
    print("Truncated number of tokens:", total_tokens())
    return True, truncated

def main():
    """
    Main function to test the count_tokens function(s).
    """
    try:
        print("Testing count_tokens with various inputs...")

        # Example test input lists
        example1 = [{"role": "user", "content": "Hello, world!"}]
        example2 = [{"role": "user", "content": "This is a longer text to count the number of tokens correctly."}]
        example3 = [
            {"role": "user", "content": "This is a shorter text to count the number of tokens correctly."}, 
            {"role": "developer", "content": "This is a developer message to count the number of tokens correctly."},
            {"role": "assistant", "content": "This is an assistant message to count the number of tokens correctly."}
        ]

        # If your count_tokens function expects a model argument, modify accordingly
        # For demonstration, assuming it's just count_tokens(text)
        model_name = "gpt-oss-120b"
        # try:
        #     print("Input 1: ", example1)
        #     truncated_message = truncate_message_by_tokens(example1, model_name)
        #     print("Output 1: ", truncated_message)
        #     print("\n\n")
        # except Exception as e:
        #     print(f"Error in count_tokens for input 1: {e}")

        # try:
        #     print("Input 2: ", example2)
        #     truncated_message = truncate_message_by_tokens(example2, model_name)
        #     print("Output 2: ", truncated_message)
        #     print("\n\n")
        # except Exception as e:
        #     print(f"Error in count_tokens for input 2: {e}")

        try:
            print("Input 3: ", example3)
            truncated_message = truncate_message_by_tokens(example3, model_name, 30)
            print("Output 3: ", truncated_message)
            print("\n\n")
        except Exception as e:
            print(f"Error in count_tokens for input 3: {e}")

        # If you have multiple token counting functions, add additional tests here

        print("count_tokens tests completed.")

    except Exception as main_e:
        print(f"Unexpected error in main testing: {main_e}")

if __name__ == "__main__":
    main()
