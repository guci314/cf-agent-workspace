---
title: Introducing System One Models & Jev
author: Diogo Almeida (founder, TypeSafe)
source: https://typesafe.ai/blog/introducing-system-one-models-and-jev
published: 2026-09-15
retrieved: 2026-09-21
type: raw-source
note: 原始资料，immutable
---

# Introducing System One Models & Jev

Today, TypeSafe AI is releasing our first **System One Model**: a new class of frontier models built to make fast, structured decisions that software can use directly.

We built a new stack entirely focused on automation: a new model architecture, parallel sampler for maximum efficiency, and training method we call **Reinforcement Learning for Calibrated Decisions (RLCD)**.

Our first public model is **Jev**, available today in early access. Jev achieves similar levels of intelligence on System One tasks compared to existing LLMs, while being two orders of magnitude faster and more efficient. While Jev gives up string generation, it's optimized for structured outputs and **can't hallucinate**.

Think of Jev as a frontier-intelligence function call: **unstructured state in, typed probabilistic decisions out.**

## Frontiers, Old and New

| Dimension | Existing LLMs | System One + Jev |
|---|---|---|
| Optimized with | RLHF / RLVR | RLCD (RL for Calibrated Decisions) |
| Optimizes for | Human preference | Calibrated decisions: epistemically honest probabilities |
| Inputs | Unstructured text, sequential messages | Unstructured data, emphasis on **structured program state** |
| Outputs | Strings / generated text. Needs parsing + validation. Can go off the rails | **Type-safe structured values.** Outputs defined in advance. Never makes type errors. All answers carry calibrated probabilities |
| Sampling | Sequential, one token at a time | **Parallel.** All outputs in a single query |
| Cost | Input $0.20–$10/MTok; output ~5x input | **Input $0.042/MTok; output FREE** |
| Speed | End-to-end 3–329 seconds | **End-to-end 70ms–500ms.** 40x–200x faster for System One shaped queries |
| Confidence | Tend to be overconfident and inconsistent | **Always communicates confidence.** Calibrated: higher confidence means higher accuracy |
| Use cases | Human-in-the-loop (chatbots, copilots, coding agents) | **AI-Powered Workflows / smart if-statements.** Classify, route, score, extract, branch |

## Evidence / Technical Results

Claims you can easily verify:
- **Speed per call**: We truly are that fast (evals run from laptops on the West Coast).
- **Cost per call**: We make our pricing transparent. We can't prove it isn't subsidized; we'll need the long-term to prove sustainability.
- **No type errors**: This would be easy to falsify with a single counter-example, but it is mathematically impossible.

## Positioning

Jev is positioned as **complementary to LLMs, not a replacement**:

- **LLM** = open-ended reasoning and generation
- **Jev** = fast, structured decisions along the way

Use it where decisions are **repeated, high volume, and the possible answers are known before the call**:

- Agent and tool routing
- Document and ticket classification
- Escalation decisions
- Eval scoring (rubric verdicts)
- Guardrails, jailbreak detection, verifying LLM outputs
- Map-reducing over big data
- Real-time applications (100ms means AI usable where UX is critical)
