"""Local retrieval with Gemini embeddings when available and deterministic keyword fallback."""
import json
import re
from typing import Any
import numpy as np
from src.article_loader import load_articles
from src.config import EMBEDDING_CACHE_PATH, GEMINI_API_KEY, EMBEDDING_MODEL


class LocalRetriever:
    def __init__(self):
        self.articles=load_articles()
        self.chunks=[{"article_id":a["id"],"title":a["title"],"category":a.get("category",""),"applies_to":a.get("applies_to",[]),"keywords":a.get("keywords",[]),"section":s["heading"],"text":s["text"]} for a in self.articles for s in a["sections"]]
        self.vectors: list[list[float]]=[]
        self.embedding_ready=False
        self._load_or_create_embeddings()

    def _load_or_create_embeddings(self) -> None:
        if not GEMINI_API_KEY: return
        texts=[self._chunk_text(c) for c in self.chunks]
        try:
            cache=json.loads(EMBEDDING_CACHE_PATH.read_text()) if EMBEDDING_CACHE_PATH.exists() else {}
            if cache.get("texts")==texts and len(cache.get("vectors",[]))==len(texts):
                self.vectors=cache["vectors"];self.embedding_ready=True;return
            from google import genai
            client=genai.Client(api_key=GEMINI_API_KEY)
            response=client.models.embed_content(model=EMBEDDING_MODEL, contents=texts)
            self.vectors=[list(item.values) for item in response.embeddings]
            EMBEDDING_CACHE_PATH.write_text(json.dumps({"texts":texts,"vectors":self.vectors}),encoding="utf-8")
            self.embedding_ready=True
        except Exception:
            self.vectors=[];self.embedding_ready=False

    @staticmethod
    def _chunk_text(chunk: dict) -> str:
        return f"{chunk['title']}\n{chunk['section']}\n{chunk['text']}"

    @staticmethod
    def _words(text: str) -> set[str]:
        return set(re.findall(r"[a-z0-9]+",text.lower()))

    def _keyword_search(self, query: str, service_type: str, limit: int) -> list[dict]:
        words=self._words(query); scored=[]
        for chunk in self.chunks:
            if service_type and service_type not in chunk["applies_to"]: continue
            corpus=self._words(" ".join(chunk["keywords"])+" "+chunk["title"]+" "+chunk["text"])
            score=len(words & corpus)
            if score: scored.append((score,chunk))
        return [dict(c, score=float(s), retrieval_method="keyword") for s,c in sorted(scored,key=lambda x:x[0],reverse=True)[:limit]]

    def search(self, query: str, service_type: str="", limit: int=4) -> list[dict[str,Any]]:
        if not self.embedding_ready:
            return self._keyword_search(query,service_type,limit)
        try:
            from google import genai
            client=genai.Client(api_key=GEMINI_API_KEY)
            response=client.models.embed_content(model=EMBEDDING_MODEL, contents=[query])
            vector=np.array(response.embeddings[0].values,dtype=float)
            matrix=np.array(self.vectors,dtype=float)
            scores=(matrix@vector)/(np.linalg.norm(matrix,axis=1)*np.linalg.norm(vector)+1e-12)
            candidates=[]
            for idx,score in enumerate(scores):
                chunk=self.chunks[idx]
                if service_type and service_type not in chunk["applies_to"]: continue
                candidates.append((float(score),chunk))
            return [dict(c,score=s,retrieval_method="embedding") for s,c in sorted(candidates,key=lambda x:x[0],reverse=True)[:limit]]
        except Exception:
            return self._keyword_search(query,service_type,limit)


retriever = LocalRetriever()
