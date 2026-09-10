#!/usr/bin/env python3
"""
Reranker LOCAL de IDENTIDADE, contrato vLLM. ⚠️ NAO E' CONFIGURACAO DE MEDICAO.

Existe para uma coisa só: provar o ENCANAMENTO do `search_knowledge()` do EverOS
sem pagar um quarto provedor. Devolve `relevance_score` decrescente na ordem em
que os documentos chegaram, isto é, **preserva a ordem do recall** (RRF/dense/
sparse) e não reordena nada.

Qualquer nDCG medido com este servidor mede o EverOS **sem** o cross-encoder que
ele exige de fábrica (`Qwen/Qwen3-Reranker-4B` na DeepInfra) — logo NAO e'
comparavel e NAO deve ir para o paper como numero do EverOS.

Contrato medido em `everos/component/rerank/vllm_provider.py`:
    POST {base_url}/rerank  {"model","query","documents"}
    -> {"results":[{"index":0,"relevance_score":0.87}, ...]}
"""

from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import sys


class H(BaseHTTPRequestHandler):
    def do_POST(self):  # noqa: N802
        if not self.path.endswith("/rerank"):
            self.send_error(404)
            return
        n = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(n) or b"{}")
        docs = body.get("documents") or []
        # Identidade: score decrescente na ordem de chegada.
        out = {
            "results": [
                {"index": i, "relevance_score": 1.0 - (i / max(1, len(docs)))}
                for i in range(len(docs))
            ]
        }
        b = json.dumps(out).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def log_message(self, *a):  # silencia
        pass


if __name__ == "__main__":
    porta = int(sys.argv[1]) if len(sys.argv) > 1 else 8799
    print(f"rerank-identidade em http://127.0.0.1:{porta}/rerank", flush=True)
    HTTPServer(("127.0.0.1", porta), H).serve_forever()
