# src/agent/tinyllama.py

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

MODEL_NAME = "microsoft/Phi-3.5-mini-instruct"

print("Loading Phi-3.5-mini-instruct model... (this may take a bit the first time)")
tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
model = AutoModelForCausalLM.from_pretrained(
    MODEL_NAME,
    torch_dtype=torch.bfloat16 if torch.cuda.is_available() else torch.float32,
    device_map="auto",
)


def call_tinyllama(prompt: str, max_new_tokens: int = 512) -> str:
    """
    Call Phi-3.5-mini-instruct with the given prompt and return only the
    generated completion (attempting to strip the echoed prompt if present).
    """
    inputs = tokenizer(prompt, return_tensors="pt").to(model.device)

    with torch.no_grad():
        outputs = model.generate(
            **inputs,
            max_new_tokens=max_new_tokens,
            do_sample=False,  # deterministic for now
        )

    full_text = tokenizer.decode(outputs[0], skip_special_tokens=True)

    # Try to strip the prompt if it's echoed
    if prompt in full_text:
        idx = full_text.find(prompt)
        completion = full_text[idx + len(prompt):].strip()
    else:
        completion = full_text.strip()

    return completion
