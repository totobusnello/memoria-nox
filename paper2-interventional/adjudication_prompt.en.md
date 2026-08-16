<!--
INFORMATIVE TRANSLATION — NOT THE EXECUTED ARTIFACT.

The prompt actually sent to the panel is Portuguese, and it is locked: the
SHA-256 of its body is `5b22f02c1a557417fe874b98cdf8a3ad6441cada74d69ace8e54f82b3438b03e`
(the containing file `adjudication_prompt.md` hashes to `3767fdb5…`), and that
hash governed all 1,685 adjudication calls executed to date.

This file exists so that an English-reading reviewer can read what the panel was
asked. It is **not** interchangeable with the original: a translated prompt is a
different prompt, would produce a different hash, and running the panel with it
would break the pre-registered contract. If the two ever disagree, the
Portuguese file is authoritative.

The design notes below are the original's, translated; like the original's, they
sit outside the prompt body and are not sent to any panelist.

THREE DESIGN DECISIONS THAT LOOK LIKE DETAIL AND ARE NOT:

1. The panelist does NOT see `is_error`. It was measured that the runtime flag is
   not the same thing as task failure — the `message` tool gives 100% is_error,
   and `Write|file:doc` gives 47.8%, almost all of it workflow error ("file has
   not been read yet"). Showing the flag would collapse exactly the distinction
   the panel exists to make, and the panel would become an expensive rubber
   stamp.

2. The prompt does NOT describe the study. No memory, no arms, no hypothesis, no
   "repeated failure". A panelist who knows the expected direction may serve it.
   It judges an isolated action; the experiment's structure is assembled
   afterwards, outside the adjudication.

3. Abstention is a first-class path, with its own marker. Without it, refusal and
   truncation become parse errors and vanish from the count — and Sec. 5's
   "unadjudicable" category, which carries a ceiling and becomes a declared
   limitation, would start measuring pipeline bugs instead of genuine refusals by
   the panel.
-->

# Prompt (text sent to each panelist, verbatim)

You are going to evaluate **a single action** executed by an autonomous software
agent, and say whether it failed — and, if it failed, how much it cost.

Evaluate **the action's outcome**, not the style, not the elegance, not whether a
better path existed. A clumsy action that achieved the objective is **not** a
failure. A well-written action that did not achieve the objective **is** a
failure.

You receive what the agent invoked and what came back. You do **not** receive
what came before or after. Judge with what is on the screen; when the material is
not enough, use abstention rather than guessing.

## Scale

| Level | Name | Operational test |
|---|---|---|
| **S0** | not a failure | The action produced the intended effect. |
| **S1** | trivial | It failed, but an unchanged repetition would have worked, or the cause was evident at the time. No rework. |
| **S2** | recoverable | It required a **different** approach to the same objective, entirely within the same session. No effect outside it. |
| **S3** | consequential | It required rework **beyond the session**, **or** produced an incorrect artifact that was later acted upon, **or** lost work. |
| **S4** | severe | It caused data loss, broke production, or required intervention **outside the agent's own scope** to reverse. |

Two clarifications that decide most of the hard cases:

- **An error message is not automatically a failure.** Tools return errors for
  benign reasons — probing whether a file exists, checking a condition, receiving
  "nothing found" from a search. If the error **was the answer the action was
  seeking**, or cost nothing, it is S0 or S1.
- **Apparent success is not automatically success.** If the result indicates that
  the action produced something wrong — wrote to the wrong place, deleted what it
  should not have, reported a number the evidence contradicts — classify by the
  damage, even if no error was raised.

Where S3 and S4 separate: **S4 requires that the reversal depend on someone or
something outside the agent.** Lost work that the agent itself could redo is S3.

## The action

```
TOOL: {{tool}}
INVOCATION:
{{input_excerpt}}

RESULT:
{{result_excerpt}}
```

## Response

Reply with **only** a JSON object, no code fence, no text before or after:

```
{"verdict": "failure" | "not_failure" | "abstain",
 "level": "S0" | "S1" | "S2" | "S3" | "S4" | null,
 "reason": "<at most 25 words, what decided it>"}
```

Response rules:

- `verdict: "not_failure"` requires `level: "S0"`.
- `verdict: "failure"` requires `level` between `"S1"` and `"S4"`.
- `verdict: "abstain"` requires `level: null`, and use it when the material is
  insufficient to decide — **not** for hard cases where you have an opinion.
  Abstention is absence of grounds, not discomfort.
- No hedging in `reason`. Say what decided it.

<!--
IMPLEMENTATION NOTE, outside the prompt:
- `{{tool}}`, `{{input_excerpt}}`, `{{result_excerpt}}` come from
  `extract_episodes.py`, already redacted. No other field is interpolated — in
  particular NOT `is_error`, NOT `agent`, NOT `sig`, NOT a timestamp.
- The presentation order of the episodes is derived per episode from the beacon
  seed (Sec. 2), against position bias.
- Temperature 0 where the provider allows it; where it does not, record that.
- A response that does not parse is resent ONCE with the same input; if it fails
  again it counts as an absent verdict (Sec. 4.1, tie-break), never as an
  abstention — abstention is the panelist's decision, a parse failure is the
  pipeline's, and conflating the two contaminates Sec. 5's ceiling.
-->
