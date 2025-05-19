import streamlit as st
import json
import requests
from dotenv import load_dotenv
import os
from openai import OpenAI
import re
from html import escape

# Load API keys from .env
load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
perplexity_api_key = os.getenv("PERPLEXITY_API_KEY")

car_forums = [
    "https://www.reddit.com/r/MechanicAdvice/",
    "https://community.cartalk.com/",
    "https://www.automotiveforums.com/",
    "https://bobistheoilguy.com/forums/",
    "https://mechanics.stackexchange.com/",
    "https://repairpal.com/",
    "https://www.autotalk.com/forums",
    "https://www.justanswer.com/car/",
    "https://www.doityourself.com/forum/passenger-cars-mini-vans-suv-service-repairs-no-trucks/",
    "https://forums.edmunds.com/",
    "https://www.carjunky.com/",
    "https://forums.anandtech.com/forums/the-garage-cars-motorcycles-and-automotive-enthusiasts.38/",
    "https://www.carforum.net/",
    "https://www.motortrend.com/forum/",
    "https://www.ratrodforums.com/",
    "https://www.dsmtuners.com/",
    "https://www.allpar.com/",
    "https://www.thirdgen.org/forums/",
    "https://www.thedieselstop.com/",
    "https://www.automotiveforums.org/",
    "https://www.bimmerfest.com/",
    "https://chevroletforum.com/", 
    "https://www.benzworld.org/",
    "https://www.vwforum.com/",
    "https://www.audiworld.com/forums/",
    "https://www.nissanforums.com/", 
    "https://honda-tech.com/forums/", 
    "https://www.toyotanation.com/"
]
import re

def extract_json_from_text(text):
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        return json.loads(match.group(0))
    else:
        raise ValueError("No valid JSON found in OpenAI response.")


def build_final_message(extracted, diagnosis_json, sources):
    #diagnosis_json = json.loads(diagnosis_json)
    diagnosis_json = extract_json_from_text(diagnosis_json)
    # Split DIY steps cleanly
    diy_steps = diagnosis_json["diy"]
    diy_steps_formatted = ""
    for step in re.findall(r"(Step\s\d+:.*?)(?=(Step\s\d+:|$))", diy_steps, re.DOTALL):
        diy_steps_formatted += f"<li>{step[0].strip()}</li>"

    
    sources_list = "<br>".join(f"- {s}" for s in sources)
        
    # Build the final HTML message
    html = f"""
    <div style='font-family:Arial, sans-serif; font-size:16px; color:#222; background-color:#f7f7f7;
                padding: 20px; border-radius: 10px; height: 350px; overflow-y: auto; overflow-x: hidden;'>

    <b>🚗 Vehicle:</b> {extracted['year']} {extracted['model']} {extracted['make']}<br><br>

    <b>🔍 Diagnosis:</b><br>{diagnosis_json['diagnosis']}<br><br>

    <b>🛠️ DIY Steps to confirm the issue:</b>
    <ul style='padding-left: 20px;'>{diy_steps_formatted}</ul><br>

    <b>💡 Forum-Suggested Solutions:</b><br>{diagnosis_json['solution']}<br><br>

    <b>⏳ Estimated Timeline:</b> {diagnosis_json['timeline']}<br>
    <b>💰 Estimated Expenses:</b> {diagnosis_json['expense']}<br><br>

    <b>📚 Sources:</b><br><br>{sources_list}<br>
    Thanks for visiting us!
    
    
    </div>
    """
    return html



def service_advisor_status(sys_msg, adv_comp_status="Thanks for sharing all the details with me! I'm now handing you over to **Gear Genie**, our expert technician."):
    sys_msg = json.loads(sys_msg)
    unk_details = [k for k, v in sys_msg.items() if v == "unknown"]
    if unk_details:
        return f"Please provide details on: {', '.join(unk_details)}"
    return adv_comp_status

def generate_perplexity_prompt_tech(extracted):
    return f"""A {extracted['year']} {extracted['model']} {extracted['make']} is reporting the following issue: {extracted['issue']}.

Please retrieve the most relevant, expert-endorsed solutions from the provided sources.

Return results in this JSON format:
[
  {{ "solution": "...", "source": "..." }},
  ...
]
"""

def generate_openai_diagnostic_prompt(extracted, context):
    return f"""
You are an expert technician for {extracted['year']} {extracted['model']} {extracted['make']}.
You have the following information available from expert forums:

{context}

Based on this provide:
1. Diagnosis or the potential root cause of the problem
2. DIY steps the user can perform to confirm the root cause in the following format:
    Step 1 .... Potential root cause
    Step 2 ...  Potential root cause
    ...
    Step N ... Potential root cause
3. Prognosis or solution steps. Indicate which steps the user can do by themselves and for which they need to visit a service centre.
4. A clean expense breakdown by UK, USA & UAE including total part costs & labor costs. An estimate of the expense region wise is sufficient.
5. An estimated timeline for the overall effort

Provide all this data in the following JSON format:
{{
  "diagnosis" : "...",
  "diy": "...",
  "solution" : "...",
  "expense": "...",
  "timeline": "..."
}}

Then, based on the above, prepare a system message to be delivered to the user:

Your car {extracted['year']} {extracted['model']} {extracted['make']} has possibly the following issues: {{diagnosis}}.
I would suggest you perform the following steps to confirm the issue: {{diy}}.
Here are solutions users facing similar symptoms have taken: {{solution}}.
Across the cases, users have reported a timeline of {{timeline}} and the expenses reported to be between {{expense}} for UK, USA & UAE respectively.
Thanks for visiting us.
"""
def clean_perplexity_output(response):
    json_match = re.search(r"\[\s*{.*?}\s*\]", response, re.DOTALL)
    if json_match:
        json_data = json.loads(json_match.group(0))
        solutions = [item["solution"] for item in json_data]
        clean_output = "\n".join(solutions)
        return clean_output
    else:
        print("No JSON block found.")
    
def call_perplexity_solutions(extracted, forums, api_key):
    prompt = generate_perplexity_prompt_tech(extracted)
    response = requests.post(
        "https://api.perplexity.ai/chat/completions",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        },
        json={
            "model": "sonar",  # or "sonar-reasoning-pro" for Sonar Pro
            "messages": [
                {"role": "system", "content": "Be precise and concise."},
                {"role": "user", "content": prompt}
            ],
            "web_search_options": {
                "num_results": 10   # <--- This requests 10 search results/sources
            }
        }
    )
    if response.status_code == 200:
        try:
            context = clean_perplexity_output(response.json()['choices'][0]['message']['content'])
            sources = response.json()['citations']
            return context, sources
        except Exception as e:
            raise ValueError(f"❌ JSON parse error: {e}")
    else:
        raise RuntimeError(f"❌ Perplexity API error: {response.status_code}")

def call_openai_diagnosis(client, extracted, context):
    prompt = generate_openai_diagnostic_prompt(extracted, context)
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content

# ----------------- Streamlit UI -----------------
st.title("🔧 AI Car Diagnosis Assistant")

st.session_state.setdefault("user_input", "")
st.session_state.setdefault("system_msg", "Hi, I'm YallaFix, your service advisor. Please describe your problem and include your car’s make, model, and year.")
st.session_state.setdefault("extracted", {})
st.session_state.setdefault("waiting_for_input", False)
st.session_state.setdefault("last_input", "")

st.text_area("🧑 Your message to YallaFix", key="user_input", height=150)

#st.markdown(
 #   f"""
  #  <div style='font-size: 1.1em; font-weight: 500; color: #222; background-color: #f7f7f7;
  #              padding: 15px; border-radius: 5px; height: 300px;
  #              overflow-y: auto; white-space: pre-wrap; word-wrap: break-word;'>
  #  💬 <b>System Message:</b><br>{st.session_state.system_msg}
  #  </div>
  #  """,
  #  unsafe_allow_html=True
#)
system_message_html = f"""
<div style="
    font-family: Arial, sans-serif;
    font-size: 16px;
    font-weight: 500;
    color: #222;
    background-color: #f7f7f7;
    padding: 15px;
    border-radius: 5px;
    height: 350px;
    overflow-y: auto;
    white-space: pre-wrap;
    word-break: break-word;
    overflow-x: hidden;
">
💬 <b>System Message:</b><br><br>{escape(st.session_state.system_msg)}
</div>
"""

st.markdown(system_message_html, unsafe_allow_html=True)


if st.button("Continue"):
    full_query = st.session_state.user_input.strip()

    if not full_query:
        st.session_state.system_msg = "Please describe your car issue."
        st.rerun()

    if st.session_state.waiting_for_input and full_query == st.session_state.last_input:
        st.session_state.system_msg = "⚠️ Still waiting for more vehicle info..."
        st.rerun()

    st.session_state.last_input = full_query

    # Step 1: Vehicle info extraction
    try:
        system_prompt = """
Extract the following from the customer's message:
- make
- model
- year
- issue (verbatim)

If any are missing, mark as "unknown".
Return in this exact JSON format:
{
  "make": "...",
  "model": "...",
  "year": "...",
  "issue": "..."
}
"""
        user_prompt = f"<|user|>{full_query}<|end|>"

        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
        )
        extracted = json.loads(response.choices[0].message.content)
        st.session_state.extracted = extracted

        status_msg = service_advisor_status(response.choices[0].message.content)
        st.session_state.system_msg = status_msg

        if "Please provide details" in status_msg:
            st.session_state.waiting_for_input = True
            st.rerun()

    except Exception as e:
        st.session_state.system_msg = f"❌ Vehicle info extraction failed: {e}"
        st.rerun()

    # Step 2: Forum search
    try:
        st.session_state.system_msg = "🔍 Gear Genie is searching expert forums for advice..."
        context, sources = call_perplexity_solutions(extracted, car_forums, perplexity_api_key)
    except Exception as e:
        st.session_state.system_msg = f"❌ Forum search failed: {e}"
        st.rerun()

    # Step 3: Diagnosis
    try:
        st.session_state.system_msg = "🧠 Gear Genie is diagnosing the issue..."
        final_message = call_openai_diagnosis(client, extracted, context)
        formatted_message= build_final_message(extracted, final_message, sources)
        print(final_message)
        #st.session_state.system_msg = final_message
        st.markdown(formatted_message, unsafe_allow_html=True)
        #st.session_state.system_msg = "Our Expert Technician Gear Genie is done & has the following inputs for you..."

        #if sources:
            #st.session_state.system_msg += "\n\n📚 Sources:\n" + "\n".join(f"- {s}" for s in sources)

    except Exception as e:
        st.session_state.system_msg = f"❌ Diagnosis failed: {e}"
        st.rerun()
