import json
import time
from ingest_data import get_answer_with_rerank

with open("evaluation.json") as f:
    data = json.load(f)

correct = 0
total_tokens = 0

def safe_query(question):
    # retry once if error
    ans, tokens = get_answer_with_rerank(question)

    if "status: error" in ans.lower():
        time.sleep(2)
        ans, tokens = get_answer_with_rerank(question)

    return ans, tokens

for item in data:
    print("\nQuestion:", item["question"])

    ans, tokens = safe_query(item["question"])
    print("AI:", ans)
    print("Tokens Used:", tokens)

    total_tokens += tokens

    ans_lower = ans.lower()
    expected = item["answer"].lower()

    is_correct = False

    # HANDLE ERROR CASE
    if "status: error" in ans_lower:
        print("⚠ LLM failed — skipping question")
        continue

    # NOT FOUND CASE
    if expected == "not found":
        if "status: not found" in ans_lower:
            is_correct = True

    # VERIFIED CASE
    else:
        if "status: verified" in ans_lower and expected in ans_lower:
            is_correct = True

    if is_correct:
        correct += 1

    time.sleep(3)

accuracy = correct / len(data)

print("\nAccuracy:", accuracy)
print("Total Tokens Used:", total_tokens)
print("Average Tokens per Question:", total_tokens // len(data))
