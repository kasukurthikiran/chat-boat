import openai
import os
from dotenv import load_dotenv
import requests
import json


load_dotenv()
openai.api_key = os.getenv("MY_API_KEY")


chat_history = []
history_file = "chat_history.txt"


function_descriptions = [
    {
        "type": "function",
        "function": {
            "name": "convert_usd_to_inr",
            "description": "Converts USD to INR using real-time exchange rates",
            "parameters": {
                "type": "object",
                "properties": {
                    "amount": {
                        "type": "number",
                        "description": "Amount in USD"
                    }
                },
                "required": ["amount"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "Get current temperature for given coordinates in Celsius.",
            "parameters": {
                "type": "object",
                "properties": {
                    "latitude": {"type": "number"},
                    "longitude": {"type": "number"}
                },
                "required": ["latitude", "longitude"]
            }
        }
    }
]


def store(question, answer):
    chat_history.append((question, answer))
    with open(history_file, "a", encoding="utf-8") as f:
        f.write(f"You: {question}\nBot: {answer}\n\n")


def get_weather(latitude, longitude):
    response = requests.get(
        f"https://api.open-meteo.com/v1/forecast?latitude={latitude}&longitude={longitude}&current=temperature_2m"
    )
    data = response.json()
    return {"temperature_celsius": data['current']['temperature_2m']}


def convert_usd_to_inr(amount):
    url = "http://api.exchangeratesapi.io/v1/latest"
    params = {
        "access_key": "",
        "symbols": "USD,INR"
    }
    response = requests.get(url, params=params)
    data = response.json()

    if response.status_code == 200 and data.get("success"):
        eur_to_usd = data["rates"]["USD"]
        eur_to_inr = data["rates"]["INR"]
        usd_to_inr = eur_to_inr / eur_to_usd
        converted = amount * usd_to_inr

        return {
            "usd_amount": amount,
            "inr_amount": round(converted, 2),
            "rate": round(usd_to_inr, 4),
            "timestamp": data.get("timestamp")
        }
    else:
        return {"error": data.get("error")}


def reasoning(user_input):
    messages = [{"role": "system", "content": "You are a helpful assistant."}]

    for q, a in chat_history:
        messages.append({"role": "user", "content": q})
        messages.append({"role": "assistant", "content": a})

    messages.append({"role": "user", "content": user_input})

   
    response = openai.chat.completions.create(
        model="gpt-4o",
        messages=messages,
        temperature=0.2,
        tools=function_descriptions,
        tool_choice="auto"
    )

    first_completion = response.choices[0].message
    results = []
    
  
    if hasattr(first_completion, "tool_calls") and first_completion.tool_calls:
        messages.append(first_completion) 
        for tool_call in first_completion.tool_calls:
            function_name = tool_call.function.name
            args = json.loads(tool_call.function.arguments)

            if function_name == "convert_usd_to_inr":
                print("i am convert_usd_to_inr")
                result = convert_usd_to_inr(**args)
            elif function_name == "get_weather":
                print("i am get_weather")
                result = get_weather(**args)
            else:
                print("i am else")
                return first_completion.content

            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "name": function_name,
                "content": json.dumps(result)
            })

       
        second_completion = openai.chat.completions.create(
            model="gpt-4o",
            messages=messages
        )

        return second_completion.choices[0].message.content
    return first_completion.content
        

def chat():
    print(" Chatbot is ready! Type 'exit' to quit.\n")
    while True:
        user_input = input("You: ")
        if user_input.lower() in ("exit", "quit"):
            print("Chat ended. Conversation saved to", history_file)
            break

        try:
            answer = reasoning(user_input)
            store(user_input, answer)
            print("Bot:", answer)
        except Exception as e:
            print("Bot: Sorry, something went wrong:", e)

if __name__ == "__main__":
    chat()
