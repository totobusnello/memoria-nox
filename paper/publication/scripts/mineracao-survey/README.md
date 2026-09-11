# Mineração do survey canônico — reprodução

Ordem: `01` → `02` → `03` → `04`. Todos falham com `exit != 0` se um controle não passar,
em vez de reportar um número sem lastro.

```sh
curl -sL -o survey.html https://arxiv.org/html/2602.06052v4
grep -c ltx_bibitem survey.html            # 535 — confere contra o parser do 01
python3 01-minera-bibitems.py              # -> survey-bibitems.json
python3 02-classifica-presenca.py <repo>   # controles (+) e (-); -> survey-ausentes.json
python3 03-admissibilidade.py              # -> candidatas.json
python3 04-resolve-localizadores.py        # arXiv IDs das que o survey cita por venue
```

**Controles que cada passo exige:**

| passo | controle | por quê |
|---|---|---|
| 01 | nº de bibitems parseadas == nº de marcas `ltx_bibitem` no HTML | ordem de atributos do LaTeXML (`id` antes de `class`) fez a primeira versão parsear **zero** |
| 01 | ≥400 bibitems com `Cited by` legível | é de onde vem a centralidade; sem isso o número vira contagem posicional aproximada |
| 02 | (+) 5 obras que citamos, 2 casando por id e 3 por título | um classificador só por id reporta 6 de 535 em vez de 17 |
| 02 | o localizador do controle tem de casar **um** bibitem | `generative agents` casa 4; a 1ª versão testou o bibitem errado e acusou falso negativo |
| 02 | (−) obra inventada sai como não citada | senão o classificador diz «já citada» para tudo |
| 03 | toda candidata com ≥4 seções tem de estar classificada | candidata sem veredito passaria como admissível por omissão |
| 04 | 2 títulos cujo arXiv ID já conhecemos devolvem esse ID | `export.arxiv.org/abs` devolve **corpo vazio** e um parser ingênuo reporta «id inexistente» |
