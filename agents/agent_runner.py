import google.generativeai as genai

genai.configure(api_key="AIzaSyBAwevLYv6HdiErVm3Wp-j4a85mMOfE1eM")

model = genai.GenerativeModel("gemini-2.5-pro")

def run_agent(prompt: str):
    response = model.generate_content(prompt)
    return response.text