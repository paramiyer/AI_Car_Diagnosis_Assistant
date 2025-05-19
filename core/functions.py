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


def service_advisor_status(sys_msg, adv_comp_status="Thanks for sharing all the details with me! I'm now handing you over to **Gear Genie**, our expert technician."):
    sys_msg = json.loads(sys_msg)
    unk_details = [k for k, v in sys_msg.items() if v == "unknown"]
    if unk_details:
        return f"Please provide details on: {', '.join(unk_details)}"
    return adv_comp_status


def generate_perplexity_prompt_tech(extracted):
    return f"""A {extracted['year']} {extracted['model']} {extracted['make']} is reporting the following issue: {extracted['issue']}.


def generate_openai_diagnostic_prompt(extracted, context):
    return f"""


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
