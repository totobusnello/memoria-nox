# Carta de apelação ao arXiv (§3.3 do pacote): diff do bloco, antes e depois

Data: 2026-10-04 (noite). Arquivo: `paper2-interventional/_sprint-2026-10-04/noxmem-apelacao-pacote.md`, §3.3, de "Submission: submit/7771319" até a assinatura.

O que mudou:
- Item 1, segundo parágrafo: passa a dizer o que não dava para conferir em 3 de setembro (dois concorrentes, alegações entre métricas diferentes, saídas por query das corridas principais fora do público) e o que dá para conferir agora; "Section 4" virou "Item 5".
- Item 3 novo, "Evidence available for checking": dataset do §6 (DOI 10.5281/zenodo.23146656, 135 números recomputados, as duas corridas sem saída, os 12 grupos não recomputáveis), código e fonte do manuscrito sob MIT, commit 09c8311 do plano, cinco versões sob o DOI de conceito, script de checagem das alegações.
- Itens 3, 4 e 5 antigos renumerados para 4, 5 e 6. Nenhum outro texto mudou.

Verificação de caracteres do bloco depois: zero travessões, asteriscos, sublinhados, chaves, colchetes, pipes e marcadores; um único "+" sem par.

```diff
--- carta-antes (v1.0.5, 1.279 palavras / 8.150 caracteres)
+++ carta-depois (1.597 palavras / 10.039 caracteres)
@@ -12,3 +12,3 @@
 
-The request rests on information that did not exist when the submission was reviewed. Two more systems were measured on the paper's benchmark after the decline, and one of them outperforms mine. The manuscript was also revised: claims that compared numbers measured under different metrics were withdrawn, several statements were corrected against the stored run artifacts, and material that described operations rather than research was moved out of the paper. Section 4 lists these changes with dates. The attached PDF is this revision, not the file submitted on 1 July.
+The request rests on what could not be checked on 3 September and can be checked now. The file reviewed then reported numbers for two competing systems and contained claims that compared numbers measured under different metrics, and the per-query outputs of its main comparison runs were not public. Since then two more systems were measured on the same corpus and queries, and one of them outperforms mine. The cross-metric claims were withdrawn, other statements were corrected against the stored run artifacts, and material on operations rather than research was moved out of the paper. The per-query outputs of the Section 6 runs are now deposited, except for two runs whose outputs were not kept, and a script recomputes 135 numbers printed in Section 6 from them (item 3). Item 5 lists the changes with dates. The attached PDF is the current revision, not the file submitted on 1 July.
 
@@ -22,3 +22,11 @@
 
-3. Fit with cs.IR
+3. Evidence available for checking
+
+- Data: the per-query outputs (retrieved ids in rank order, scores, latency, errors) of the Section 6 runs, except two: the first comparison run, of 15 June 2026 (n = 100 per dataset), whose outputs were not retained, as Section 6.3 states, and the nox-mem half of a 20-query smoke test, whose output file was overwritten. The outputs are at Zenodo, DOI 10.5281/zenodo.23146656, with the scoring code and a script that recomputes 135 numbers printed in Section 6 and compares each with the paper. All 135 match. For the 15 June run the script checks only the arithmetic of three printed differences. The record lists the 12 groups of Section 6 figures it cannot recompute, each with the reason; they include service settings, a console log that is not archived, and figures quoted from Section 5. It contains no question or passage text from the benchmarks, for licensing reasons.
+- Code: the evaluation harness and the manuscript source are public at github.com/totobusnello/memoria-nox under the MIT license.
+- Protocol: the plan mentioned in item 2 entered that repository in commit 09c8311 on 21 May 2026 (00:21 UTC on 22 May), before the first run on 23 May.
+- Versions: the revisions since 7 September 2026 are archived as five versions under the concept DOI 10.5281/zenodo.22649268, and paper/CHANGELOG.md in the repository (partly in Portuguese) records what changed in each.
+- Claims: a script in the paper directory of the repository runs 21 mechanical checks on the manuscript's claims, and it passes on the current text.
+
+4. Fit with cs.IR
 
@@ -26,3 +34,3 @@
 
-4. Changes since the submission, with dates
+5. Changes since the submission, with dates
 
@@ -37,3 +45,3 @@
 
-5. Disclosure of tool use
+6. Disclosure of tool use
 
```
