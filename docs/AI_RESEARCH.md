# AI-assisted research and reported guard interruptions

An agent is useful for cross-referencing disassembly, checking data flow, writing
bounded tooling, reviewing undo paths and analysing captures. It is not a substitute
for original evidence or for knowing which operation will actually run.

## Recorded model and effort

The current local Codex session metadata, inspected on 14 November 2026, records
**`gpt-6-astra`, reasoning effort `xhigh`**. This is the session's recorded
selection, not a backend attestation or proof of every model used in every
historical turn. The host's current default configuration instead lists
`gpt-6.1-sol` / `xhigh`; a default is not evidence that this thread used that model.

For reproducing a review, record the exact UI/API model identifier, reasoning
effort, tool permissions, source revision, inputs and test results. GPT-6 Astra
at xhigh is a documented example from this work, not a mandatory choice or a
safety certification. A capable alternative should be able to inspect source,
run offline checks, admit uncertainty and distinguish inferred behavior from
physical evidence. Use more effort for uncertain controller/reversal analysis,
and ordinary settings for straightforward packaging; more thinking does not
automatically make a larger patch better.

Official descriptions of effort and configuration are available in
[OpenAI's reasoning guide](https://developers.openai.com/api/docs/guides/reasoning)
and [configuration reference](https://learn.chatgpt.com/docs/config-file/config-reference).

## The reported interruptions

| Report | What can be stated accurately |
| --- | --- |
| Claude | The owner reports that a model they identify as **“Claude Opus 5.5”** refused assistance due to a “cyber” flag. The original refusal transcript and exact provider model identifier were not supplied for verification. This is an attributed user report, not an independently reproduced vendor-policy result. |
| Codex | During the earlier research, the owner reported a hidden-content notice and recalled the specific message: **“Daybreak isn’t available for Astra. Some cybersecurity requests may still be limited.”** The preceding hidden-content wording was explicitly from memory. The exact triggering classification was not available. |

These reports do not establish that the camera project is malicious, that a
particular provider always refuses it, or that work accepted by another agent
is safe. Do not infer an internal rule or exact causal trigger from the visible
notice alone. The interruption was not retried as an exercise in defeating a
guard.

## What to do if a tool or agent declines

Back off to work that materially reduces the operational scope: published
firmware comparison, architecture diagrams, saved-log interpretation, existing
RAW analysis, synthetic offline tests, or a documented ordinary camera interface.
Explain device ownership, the exact task and boundaries honestly. Keep live
camera changes separate and explicit. If the necessary device operation remains
outside the tool's permitted scope, stop that operation and use a qualified
human review or supported vendor route.

“Less sensitive” here means a genuinely narrower task, not disguising the same
request, hiding its purpose, fragmenting it to evade review, disabling safeguards,
or shopping for a model specifically to bypass a refusal.

## What a good review should deliver

- A trace from changed bytes to the menu/controller/capture behavior.
- A separation of target commands, sampled digital feedback and measured optical motion.
- Exact source/version assumptions and a visible, limited patch.
- An inverse and a clear statement of when that inverse can run.
- Offline tests that exercise failures, rather than merely echo the intended implementation.
- Contradicting evidence, uncertainty and failed trials retained alongside successes.

If an agent cannot explain these, do more source work or ask a better-qualified
reviewer. Do not install guessed offsets simply because the answer sounds assured.
