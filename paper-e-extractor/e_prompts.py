"""Paper E writing criteria. C0 and C2 are imported verbatim from the Paper 3 runner (frozen at tag
paper3-prereg-v1.3); P is new and is fixed here, before any call that uses it.

P ("purpose only") keeps C0's header, output format, importance scale, ceiling of 10 items and
the >= 0.5 filter, and replaces every rule about WHAT to keep (C0's category list and its ignore
list) with one paragraph that states what the memories will be used for. The model decides what
serves that purpose. C2 is the opposite end: C0 plus two paragraphs of explicit rules.
"""
import hashlib
import importlib.util
import pathlib

HERE = pathlib.Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("lme_run", HERE.parent / "paper3-construction" / "lme-run.py")
lme = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(lme)

HEADER = "Você é um extrator de memória de conversas de IA.\n"
assert lme.DISTILL_SYSTEM.startswith(HEADER)
_tail = lme.DISTILL_SYSTEM[lme.DISTILL_SYSTEM.index(lme._ANCHOR):]

PURPOSE_PARAGRAPH = """As memórias que você extrair serão, mais tarde, a única fonte de um assistente que vai responder perguntas do usuário sobre o que ele contou e sobre o que foi dito nesta conversa. A conversa em si não estará mais disponível. Decida você, pelo conteúdo desta conversa, o que precisa ser guardado para que essas perguntas possam ser respondidas.

"""
DISTILL_SYSTEM_P = HEADER + PURPOSE_PARAGRAPH + _tail

PROMPTS = {"C0": lme.PROMPTS["C0"], "C2": lme.PROMPTS["C2"], "P": DISTILL_SYSTEM_P}

# C2 must be byte-identical to what the Paper 3 confirmatory run used (CONFIRM-RESULT.md).
C2_SHA256 = "325342a36e742f1e844b7c3792dae3eb47a76879c501678b576cd6df2cc8089d"
assert hashlib.sha256(PROMPTS["C2"].encode()).hexdigest() == C2_SHA256


def sha(crit):
    return hashlib.sha256(PROMPTS[crit].encode()).hexdigest()


if __name__ == "__main__":
    for c in PROMPTS:
        print(c, len(PROMPTS[c]), sha(c))
    print("\n--- P ---\n" + DISTILL_SYSTEM_P)
