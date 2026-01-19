import os
from openai import OpenAI
from groq import Groq

# client = OpenAI(
#     api_key=os.environ.get("OPENAI_API_KEY"),
# )

client = OpenAI(
    api_key=os.environ.get("GROQ_API_KEY"),
    base_url="https://api.groq.com/openai/v1"
)

def run_test():

    input_list = [
        {
            "role": "developer",
            "content": "You are a master comedian. You will be given a joke and you will need to tell it in a funny way."
        },
        {
            "role": "user",
            "content": [{
                "type": "input_text",
                "text": "Why did the chicken cross the road? To get to the other side."
            }]
        }
    ]

    response = client.responses.create(
        model="openai/gpt-oss-120b",
        input=input_list,
        # tool_choice = "none",
        # truncation="auto",
    )

    if response.output_text: # This works with Groq
        input_list.append({
            "role": "assistant",
            "content": response.output_text
        })
    
    # if response.output_text: # This works with OpenAI, not Groq
    #     input_list.append({
    #         "role": "assistant",
    #         "content": [
    #             {
    #                 "type": "output_text",
    #                 "text": response.output_text
    #             }
    #         ]
    #     })
    
    # input_list.extend(response.output) # This works with Groq
            
    # print(f"Response")
    # for el in response.output:
    #     print(f"el: {el.role} \n {el.content} \n\n")   

    # input_list += [{"role": el.role, "content": el.content} for el in response.output if el.type == "message"]
    

    input_list.append({
        "role": "user",
        "content": "Improve it further."
    })

    print(input_list)
    response = client.responses.create(
        model="openai/gpt-oss-120b",
        input=input_list,
        # tool_choice = "none",
        # truncation="auto",
    )

    # print(response.output_text)
 
   
if __name__ == "__main__":
    run_test()
