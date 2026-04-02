import google.generativeai as genai

genai.configure(api_key="AIzaSyBV50gvOhXMo2BUyTXt5Yg65mcXHvZf-q0")

model = genai.GenerativeModel("gemini-2.5-pro")

def run_agent(prompt: str):
    response = model.generate_content(prompt)
    return response.text