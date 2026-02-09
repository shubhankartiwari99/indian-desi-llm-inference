from app.model_loader import ModelLoader
loader = ModelLoader("artifacts/alignment_lora/final")
_, tokenizer = loader.load()

sentinel_tokens = []
for tid in range(len(tokenizer.get_vocab())):
    tok = tokenizer.convert_ids_to_tokens(tid)
    if "<extra_id_" in tok:
        sentinel_tokens.append((tid, tok))

print("Found sentinel-like tokens (id, token):")
for tid, tok in sentinel_tokens[:100]:
    print(tid, tok)
print("Total sentinel-like tokens:", len(sentinel_tokens))
