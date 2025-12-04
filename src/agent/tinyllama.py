# src/tinyllama.py
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM

MODEL_NAME = "microsoft/Phi-3.5-mini-instruct"

# Load tokenizer & model ONCE globally
tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
model = AutoModelForCausalLM.from_pretrained(
    MODEL_NAME,
    torch_dtype=torch.float16,
    device_map="auto",
)

def call_tinyllama(prompt: str, max_new_tokens: int = 256) -> str:
    """
    Generate text using TinyLlama, returning ONLY the new generated text,
    not including the prompt.
    """

    # Encode prompt
    inputs = tokenizer(prompt, return_tensors="pt").to(model.device)
    input_ids = inputs["input_ids"][0]

    # Generate continuation
    outputs = model.generate(
        **inputs,
        max_new_tokens=max_new_tokens,
        do_sample=True,
        top_p=0.9,
        temperature=0.7,
        pad_token_id=tokenizer.eos_token_id,
    )

    # Extract ONLY the model's generated continuation
    generated = outputs[0][len(input_ids):]

    # Decode only new text
    text = tokenizer.decode(generated, skip_special_tokens=True).strip()

    return text

def clean_model_output(text):
    """
    Remove sections like 'Example:', 'EXAMPLE:', 'Output:', 'Sleep logs:', etc.
    Keep only days that match the pattern 'Monday:', 'Tuesday:', etc.
    """
    days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

    cleaned_lines = []
    keep = False

    for line in text.splitlines():
        line_strip = line.strip()

        # Start keeping when we see a day header
        if any(line_strip.startswith(day + ":") for day in days):
            keep = True

        if keep:
            cleaned_lines.append(line_strip)

    return "\n".join(cleaned_lines)

