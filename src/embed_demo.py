from sentence_transformers import SentenceTransformer, util

model = SentenceTransformer("BAAI/bge-small-en-v1.5")

sentences = [
    "Azure revenue increased 48%",
    "Microsoft's cloud computing platform grew almost half year over year",
    "The company returned cash to shareholders through dividends",
]
embeddings = model.encode(sentences, normalize_embeddings=True)

print("Vector shape:", embeddings.shape)
print("Max input length (tokens):", model.max_seq_length)
print("Azure vs cloud growth:", float(util.cos_sim(embeddings[0], embeddings[1])))
print("Azure vs dividends:   ", float(util.cos_sim(embeddings[0], embeddings[2])))