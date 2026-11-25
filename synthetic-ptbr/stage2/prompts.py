# Prompts copied from the sources named in PREREGISTRATION.md §3, extracted by code from the
# commits given there; test-stage2.py re-extracts them and fails on any difference.

CLOSED = 'Responda à pergunta abaixo com o que você já sabe. Não há documento nenhum.\nSe não souber, ou se a resposta depender de um sistema interno específico que você não conhece,\nresponda exatamente NAO SEI.\n\nPERGUNTA: {q}\n\nDevolva JSON: {{"resposta": "<sua resposta ou NAO SEI>"}}'

ORACLE = 'Você está auditando uma pergunta candidata a entrar num conjunto de avaliação.\n\nPERGUNTA: {q}\n\nTRECHO (única fonte permitida):\n---\n{texto}\n---\n\nRESPOSTA SEM FONTE (o que um modelo respondeu sem ver trecho nenhum):\n---\n{sem}\n---\n\nFaça três coisas:\n1. Responda à pergunta usando APENAS o TRECHO.\n2. Copie, VERBATIM e sem alterar um caractere, o pedaço do TRECHO que sustenta a sua resposta.\n   Se o TRECHO não sustenta resposta nenhuma, deixe a citação vazia.\n3. Diga se a RESPOSTA SEM FONTE já contém, em substância, a mesma resposta que o TRECHO dá.\n   "NAO SEI", resposta vaga, ou resposta sobre outra coisa NÃO contam como já contendo.\n\nDevolva JSON:\n{{"resposta_com_fonte": "<...>",\n  "citacao_verbatim": "<trecho copiado ou string vazia>",\n  "trecho_responde": true|false,\n  "sem_fonte_ja_responde": true|false,\n  "motivo": "<uma frase>"}}'

REPASS = 'PERGUNTA: {q}\n\nTRECHO:\n---\n{t}\n---\n\nRESPOSTA SEM FONTE (o que um modelo respondeu sem ver trecho nenhum):\n---\n{sem}\n---\n\n1. O TRECHO contém a resposta para a PERGUNTA?\n2. Se sim, copie **apenas as 8 primeiras palavras** da frase do TRECHO que sustenta a resposta.\n   Exatamente como aparecem, sem reescrever, sem juntar pedaços de lugares diferentes,\n   sem acrescentar reticências. Oito palavras, nada mais.\n3. A RESPOSTA SEM FONTE já contém, em substância, a mesma resposta que o TRECHO dá?\n   "NAO SEI", resposta vaga ou sobre outra coisa NÃO contam como já contendo.\n\nDevolva JSON:\n{{"trecho_responde": true|false, "oito_palavras": "<...>", "sem_fonte_ja_responde": true|false,\n  "motivo": "<uma frase>"}}'

POOL = 'PERGUNTA: {q}\n\nTRECHO:\n---\n{t}\n---\n\n1. O TRECHO contém a resposta para a PERGUNTA? Não basta tratar do mesmo assunto.\n2. Se sim, copie **apenas as 8 primeiras palavras** da frase do TRECHO que sustenta a resposta,\n   exatamente como aparecem, sem reescrever e sem juntar pedaços de lugares diferentes.\n\nDevolva JSON: {{"trecho_responde": true|false, "oito_palavras": "<...>", "motivo": "<uma frase>"}}'

REG_PREDICATE = 'O TRECHO contem a resposta para esta PERGUNTA: {q}\nNao basta tratar do mesmo assunto: tem de conter a resposta.'

REG_LEVEL_Q = 'Qual destes descreve melhor o TRECHO em relacao a PERGUNTA: {q}'

REG_LEVELS = [{'label': 'fora', 'description': 'O TRECHO nao trata do assunto da PERGUNTA.'}, {'label': 'vizinho', 'description': 'O TRECHO trata do mesmo assunto e usa os mesmos termos, mas nenhuma frase dele responde a PERGUNTA.'}, {'label': 'parcial', 'description': 'Alguma frase do TRECHO responde em parte, faltando um dado que a PERGUNTA pede.'}, {'label': 'completo', 'description': 'Alguma frase do TRECHO responde a PERGUNTA por inteiro.'}]

ENVELOPE_PRED = 'O TRECHO contem a resposta para esta PERGUNTA: {q}\nNao basta tratar do mesmo assunto: tem de conter a resposta.'

GOLD_RESPONDE = 'O TRECHO contem informacao que responde, total ou parcialmente, a esta PERGUNTA: {q}\nConta como responder trazer o dado pedido, ainda que com outra redacao. NAO conta mencionar apenas o assunto sem o dado.'
